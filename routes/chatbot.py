"""
Chatbot Blueprint — Library Assistant API
Routes:  POST /api/chat

Architecture:
  1. Validate & sanitise user message (server-side, no trust of client).
  2. Send message to OpenAI to extract structured search intent (title/author/
     category/isbn/availability intent).  AI never touches the DB directly.
  3. Query the Book model via SQLAlchemy using the extracted filters.
  4. Return real DB records as JSON — the AI may optionally summarise the
     results in a friendly sentence, but numbers/titles/etc. always come
     from the DB, never from the AI.
  5. Graceful fallback: if the OpenAI key is absent or the call fails, the
     endpoint falls back to plain keyword search so the chatbot still works.

Security:
  - API key loaded from environment only (never embedded in source).
  - Input length capped at 500 characters.
  - Simple in-memory rate limiter (10 requests / minute per IP).
  - All DB queries use parameterised ORM calls — no raw SQL.
  - Only Book fields are returned; member / loan / user data are never sent
    to the AI or returned via this endpoint.
"""

import os
import json
import time
import logging
from collections import defaultdict
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required
from sqlalchemy import or_

from extensions import db
from models.book import Book

logger = logging.getLogger(__name__)

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/api')

# ---------------------------------------------------------------------------
# Simple in-memory rate limiter  (10 req / 60 s per IP)
# ---------------------------------------------------------------------------
_RATE_LIMIT_REQUESTS = 10
_RATE_LIMIT_WINDOW   = 60          # seconds
_rate_store: dict[str, list[float]] = defaultdict(list)

def _is_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    timestamps = _rate_store[ip]
    # remove timestamps older than the window
    _rate_store[ip] = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]
    if len(_rate_store[ip]) >= _RATE_LIMIT_REQUESTS:
        return True
    _rate_store[ip].append(now)
    return False


# ---------------------------------------------------------------------------
# OpenAI helper  (graceful degradation when key is absent)
# ---------------------------------------------------------------------------
def _extract_intent_via_ai(user_message: str) -> dict:
    """
    Call OpenAI to parse natural-language query into structured filters.
    Returns a dict like:
        {
          "intent": "search",        # search | availability | copies | location | general
          "title": "Clean Code",
          "author": null,
          "category": null,
          "isbn": null,
          "keywords": ["clean", "code"]
        }
    On any failure returns {"intent":"search", "keywords": [word, ...]}
    """
    api_key = os.environ.get('OPENAI_API_KEY', '').strip()
    model   = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini').strip()

    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    try:
        from openai import OpenAI          # import here so app starts without openai
        client = OpenAI(api_key=api_key)

        system_prompt = (
            "You are a library search assistant. "
            "Parse the user's question and return ONLY a JSON object with these keys "
            "(use null if not present): "
            "intent (one of: search | availability | copies | location | general), "
            "title (string or null), "
            "author (string or null), "
            "category (string or null), "
            "isbn (string or null), "
            "keywords (array of strings, max 5 words from the query). "
            "Do NOT include any explanation. Output valid JSON only."
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0,
            max_tokens=200,
            timeout=8,
        )
        raw = response.choices[0].message.content.strip()
        # Strip possible markdown code fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        intent_data = json.loads(raw)
        # Sanitise: only allow expected keys and string types
        allowed_keys = {"intent", "title", "author", "category", "isbn", "keywords"}
        clean = {k: v for k, v in intent_data.items() if k in allowed_keys}
        # Ensure keywords is always a list of strings
        if not isinstance(clean.get("keywords"), list):
            clean["keywords"] = []
        clean["keywords"] = [str(w) for w in clean["keywords"][:5]]
        return clean

    except Exception as exc:
        logger.warning("OpenAI intent extraction failed: %s", exc)
        raise


def _fallback_intent(user_message: str) -> dict:
    """Keyword-based fallback intent when AI is unavailable."""
    # Common English stop-words that should not be used as DB search terms
    STOP_WORDS = {
        'find', 'show', 'search', 'look', 'get', 'list', 'give', 'tell',
        'me', 'about', 'the', 'a', 'an', 'and', 'or', 'in', 'on', 'of',
        'do', 'you', 'have', 'is', 'are', 'for', 'by', 'any', 'all',
        'that', 'this', 'with', 'from', 'book', 'books', 'written',
        'how', 'many', 'can', 'i', 'please', 'some', 'what', 'which',
    }
    words = user_message.lower().split()
    intent = "search"
    if any(w in words for w in ("available", "availability", "free")):
        intent = "availability"
    elif any(w in words for w in ("copies", "copy")):
        intent = "copies"
    elif any(w in words for w in ("where", "shelf", "location")):
        intent = "location"

    # Filter stop-words and short words; keep meaningful terms
    meaningful = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    return {
        "intent":   intent,
        "title":    None,
        "author":   None,
        "category": None,
        "isbn":     None,
        "keywords": meaningful[:5],
    }


# ---------------------------------------------------------------------------
# Database query
# ---------------------------------------------------------------------------
def _search_books(intent: dict) -> list[Book]:
    """
    Build a safe SQLAlchemy query from the structured intent.
    Returns up to 10 Book objects.
    """
    query = Book.query
    conditions = []

    title    = (intent.get("title")    or "").strip()
    author   = (intent.get("author")   or "").strip()
    category = (intent.get("category") or "").strip()
    isbn     = (intent.get("isbn")     or "").strip()
    keywords = intent.get("keywords",  [])

    if isbn:
        query = query.filter(Book.isbn.ilike(f"%{isbn}%"))
    else:
        if title:
            conditions.append(Book.title.ilike(f"%{title}%"))
        if author:
            conditions.append(Book.author.ilike(f"%{author}%"))
        if category:
            conditions.append(Book.category.ilike(f"%{category}%"))

        if not conditions and keywords:
            # Full-text fallback across searchable columns using OR for each keyword
            kw_filters = []
            for kw in keywords:
                p = f"%{kw}%"
                kw_filters.append(or_(
                    Book.title.ilike(p),
                    Book.author.ilike(p),
                    Book.category.ilike(p),
                    Book.description.ilike(p),
                ))
            if kw_filters:
                # Combine all keyword filters with OR so any match qualifies
                query = query.filter(or_(*kw_filters))


        if conditions:
            query = query.filter(or_(*conditions))

    # For availability intent, prioritise available books
    if intent.get("intent") == "availability":
        query = query.order_by(Book.available_copies.desc())
    else:
        query = query.order_by(Book.title.asc())

    return query.limit(10).all()


# ---------------------------------------------------------------------------
# Serialise a Book safely (no ORM objects cross the boundary)
# ---------------------------------------------------------------------------
def _book_to_card(book: Book) -> dict:
    try:
        view_url = url_for('books.view', book_id=book.id)
    except Exception:
        view_url = None

    return {
        "id":               book.id,
        "title":            book.title,
        "author":           book.author,
        "category":         book.category,
        "isbn":             book.isbn or None,
        "publisher":        book.publisher or None,
        "publication_year": book.publication_year,
        "shelf_location":   book.shelf_location or None,
        "total_copies":     book.total_copies,
        "available_copies": book.available_copies,
        "is_available":     book.is_available,
        "view_url":         view_url,
    }


# ---------------------------------------------------------------------------
# Generate a friendly text response  (optionally via AI, otherwise template)
# ---------------------------------------------------------------------------
def _generate_response_text(user_message: str, books: list[Book], intent: dict) -> str:
    """Use AI to write a one-sentence summary if configured; otherwise use templates."""
    api_key = os.environ.get('OPENAI_API_KEY', '').strip()
    model   = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini').strip()

    if api_key and books:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            # Send only non-sensitive, already-public book metadata
            books_summary = "; ".join(
                f'"{b.title}" by {b.author} ({b.available_copies} of {b.total_copies} copies available)'
                for b in books[:5]
            )
            prompt = (
                f'The user asked: "{user_message}". '
                f'The library database returned these matching books: {books_summary}. '
                "Write a friendly one-to-two sentence response summarising what was found. "
                "Do not invent any additional books or change the numbers. "
                "Keep it under 60 words."
            )
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=100,
                timeout=8,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            logger.warning("AI response generation failed: %s", exc)

    # Template fallback
    count = len(books)
    if count == 0:
        return (
            "Sorry, I couldn't find a matching book in our library. "
            "Please try another title, author, ISBN, or category."
        )
    if intent.get("intent") == "availability":
        avail = sum(1 for b in books if b.is_available)
        return (
            f"I found {count} book(s) matching your query. "
            f"{avail} of them currently have copies available."
        )
    return f"I found {count} matching book(s) in our library catalog."


# ---------------------------------------------------------------------------
# Main chat endpoint
# ---------------------------------------------------------------------------
@chatbot_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """
    POST /api/chat
    Body (JSON): { "message": "..." }
    Response   : { "reply": "...", "books": [...], "intent": "..." }
    """
    # --- Rate limit ---
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    if _is_rate_limited(client_ip):
        return jsonify({
            "error":  "rate_limited",
            "reply":  "You're sending messages too quickly. Please wait a moment and try again.",
            "books":  [],
            "intent": "error",
        }), 429

    # --- Parse & validate input ---
    data = request.get_json(silent=True) or {}
    raw_message = data.get("message", "")

    if not isinstance(raw_message, str):
        return jsonify({"error": "invalid_input", "reply": "Invalid message format.", "books": [], "intent": "error"}), 400

    message = raw_message.strip()

    if not message:
        return jsonify({
            "reply":  "Please type a question or book title to search for.",
            "books":  [],
            "intent": "empty",
        }), 200

    if len(message) > 500:
        return jsonify({
            "reply":  "Your message is too long. Please keep it under 500 characters.",
            "books":  [],
            "intent": "error",
        }), 400

    # --- Intent extraction (AI with fallback) ---
    ai_available = bool(os.environ.get('OPENAI_API_KEY', '').strip())
    try:
        intent = _extract_intent_via_ai(message)
    except Exception:
        intent = _fallback_intent(message)
        ai_available = False

    # --- DB search ---
    try:
        books = _search_books(intent)
    except Exception as exc:
        logger.error("Database search error: %s", exc)
        return jsonify({
            "reply":  "A database error occurred. Please try again.",
            "books":  [],
            "intent": intent.get("intent", "error"),
        }), 500

    # --- Build response ---
    reply_text = _generate_response_text(message, books, intent)

    return jsonify({
        "reply":        reply_text,
        "books":        [_book_to_card(b) for b in books],
        "intent":       intent.get("intent", "search"),
        "ai_powered":   ai_available,
        "result_count": len(books),
    }), 200


# ---------------------------------------------------------------------------
# Quick health check (used by chatbot.js to detect if AI is configured)
# ---------------------------------------------------------------------------
@chatbot_bp.route('/chat/status', methods=['GET'])
@login_required
def chat_status():
    ai_key = os.environ.get('OPENAI_API_KEY', '').strip()
    return jsonify({
        "online":     True,
        "ai_enabled": bool(ai_key),
        "model":      os.environ.get('OPENAI_MODEL', 'gpt-4o-mini') if ai_key else None,
    }), 200
