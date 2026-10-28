/**
 * Library Assistant Chatbot — Frontend JS
 * File: static/js/chatbot.js
 *
 * Security notes:
 *  - All user/AI text is inserted via textContent / createTextNode — never
 *    innerHTML with untrusted data.  Book detail strings come from the
 *    server (our own DB) and are still set via DOM text APIs.
 *  - CSRF token read from the <meta> tag already present in base.html.
 *  - No API keys anywhere in this file.
 */

(function () {
    'use strict';

    // ── Constants ─────────────────────────────────────────────────────────
    const CHAT_API    = '/api/chat';
    const STATUS_API  = '/api/chat/status';
    const MAX_CHARS   = 500;
    const SUGGESTIONS = [
        'Do you have Python books?',
        'Find books about Machine Learning',
        'Show available Data Science books',
        'Books by Robert C. Martin',
        'Find book by ISBN',
        'Where is this book located?',
        'How many copies are available?',
    ];

    // ── State ─────────────────────────────────────────────────────────────
    let isOpen       = false;
    let isTyping     = false;
    let aiEnabled    = false;
    let unreadCount  = 0;

    // ── DOM refs — resolved after DOMContentLoaded ─────────────────────
    let toggleBtn, unreadBadge, chatWindow, messagesArea,
        inputEl, sendBtn, suggestionsBar;

    // ── CSRF token from meta tag ────────────────────────────────────────
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    // ── Time helper ─────────────────────────────────────────────────────
    function nowTime() {
        return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // ── Toggle window open/close ────────────────────────────────────────
    function toggleWindow() {
        isOpen = !isOpen;
        chatWindow.classList.toggle('open', isOpen);
        const icon = toggleBtn.querySelector('.cb-icon');

        if (isOpen) {
            icon.className = 'cb-icon bi bi-x-lg';
            unreadCount = 0;
            unreadBadge.classList.remove('visible');
            inputEl.focus();
            toggleBtn.setAttribute('aria-expanded', 'true');
        } else {
            icon.className = 'cb-icon bi bi-chat-dots-fill';
            toggleBtn.setAttribute('aria-expanded', 'false');
        }
    }

    // ── Scroll messages to bottom ───────────────────────────────────────
    function scrollBottom() {
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }

    // ── Build a message wrapper ──────────────────────────────────────────
    function addMessage(role, text, extraNode) {
        // Remove empty state if present
        const empty = messagesArea.querySelector('.cb-empty-state');
        if (empty) empty.remove();

        const wrapper = document.createElement('div');
        wrapper.className = `cb-msg ${role}`;

        const bubble = document.createElement('div');
        bubble.className = 'cb-bubble';
        bubble.textContent = text;          // safe — no innerHTML
        wrapper.appendChild(bubble);

        if (extraNode) wrapper.appendChild(extraNode);

        const ts = document.createElement('span');
        ts.className = 'cb-timestamp';
        ts.textContent = nowTime();
        wrapper.appendChild(ts);

        messagesArea.appendChild(wrapper);
        scrollBottom();
        return wrapper;
    }

    // ── Build book cards from API results ───────────────────────────────
    function buildBookCards(books) {
        if (!books || books.length === 0) return null;

        const container = document.createElement('div');
        container.className = 'cb-book-cards';

        books.forEach(book => {
            const card = document.createElement('div');
            card.className = 'cb-book-card';

            // Title
            const title = document.createElement('p');
            title.className = 'cb-book-title';
            title.textContent = book.title;
            card.appendChild(title);

            // Author / year
            const meta = document.createElement('p');
            meta.className = 'cb-book-meta';
            let metaText = `by ${book.author}`;
            if (book.publication_year) metaText += ` · ${book.publication_year}`;
            meta.textContent = metaText;
            card.appendChild(meta);

            // Badges row
            const badges = document.createElement('div');
            badges.className = 'cb-book-badges';

            const availBadge = document.createElement('span');
            availBadge.className = `cb-badge ${book.is_available ? 'cb-badge-available' : 'cb-badge-unavailable'}`;
            availBadge.textContent = book.is_available ? '✓ Available' : '✗ Not Available';
            badges.appendChild(availBadge);

            if (book.category) {
                const catBadge = document.createElement('span');
                catBadge.className = 'cb-badge cb-badge-category';
                catBadge.textContent = book.category;
                badges.appendChild(catBadge);
            }

            const copiesBadge = document.createElement('span');
            copiesBadge.className = 'cb-badge cb-badge-copies';
            copiesBadge.textContent = `${book.available_copies}/${book.total_copies} copies`;
            badges.appendChild(copiesBadge);

            card.appendChild(badges);

            // Details
            if (book.isbn) {
                const isbnLine = document.createElement('p');
                isbnLine.className = 'cb-book-detail';
                const s = document.createElement('strong');
                s.textContent = 'ISBN: ';
                isbnLine.appendChild(s);
                isbnLine.appendChild(document.createTextNode(book.isbn));
                card.appendChild(isbnLine);
            }

            if (book.shelf_location) {
                const shelfLine = document.createElement('p');
                shelfLine.className = 'cb-book-detail';
                const s = document.createElement('strong');
                s.textContent = 'Shelf: ';
                shelfLine.appendChild(s);
                shelfLine.appendChild(document.createTextNode(book.shelf_location));
                card.appendChild(shelfLine);
            }

            if (book.publisher) {
                const pubLine = document.createElement('p');
                pubLine.className = 'cb-book-detail';
                const s = document.createElement('strong');
                s.textContent = 'Publisher: ';
                pubLine.appendChild(s);
                pubLine.appendChild(document.createTextNode(book.publisher));
                card.appendChild(pubLine);
            }

            // View link
            if (book.view_url) {
                const link = document.createElement('a');
                link.className = 'cb-view-link';
                link.href = book.view_url;
                link.target = '_blank';
                link.rel = 'noopener noreferrer';

                const icon = document.createElement('i');
                icon.className = 'bi bi-box-arrow-up-right';
                link.appendChild(icon);
                link.appendChild(document.createTextNode(' View Details'));
                card.appendChild(link);
            }

            container.appendChild(card);
        });

        return container;
    }

    // ── Typing indicator ─────────────────────────────────────────────────
    let typingEl = null;
    function showTyping() {
        if (typingEl) return;
        const wrapper = document.createElement('div');
        wrapper.className = 'cb-msg assistant';
        const indicator = document.createElement('div');
        indicator.className = 'cb-typing';
        [0, 1, 2].forEach(() => {
            const dot = document.createElement('div');
            dot.className = 'cb-dot';
            indicator.appendChild(dot);
        });
        wrapper.appendChild(indicator);
        messagesArea.appendChild(wrapper);
        typingEl = wrapper;
        scrollBottom();
    }

    function hideTyping() {
        if (typingEl) {
            typingEl.remove();
            typingEl = null;
        }
    }

    // ── Send message ─────────────────────────────────────────────────────
    async function sendMessage() {
        const text = inputEl.value.trim();
        if (!text || isTyping) return;
        if (text.length > MAX_CHARS) {
            addMessage('error', `Message too long (${text.length}/${MAX_CHARS} chars). Please shorten it.`);
            return;
        }

        // Clear input, show user bubble
        inputEl.value = '';
        autoResizeInput();
        addMessage('user', text);

        // Hide suggestions after first real message
        if (suggestionsBar) suggestionsBar.style.display = 'none';

        // Loading state
        isTyping = true;
        sendBtn.disabled = true;
        showTyping();

        try {
            const resp = await fetch(CHAT_API, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({ message: text }),
            });

            hideTyping();

            if (resp.status === 429) {
                addMessage('error', '⏳ You\'re sending messages too fast. Please wait a moment.');
                return;
            }

            if (!resp.ok) {
                addMessage('error', 'Something went wrong. Please try again in a moment.');
                return;
            }

            const data = await resp.json();
            const bookCards = buildBookCards(data.books);
            addMessage('assistant', data.reply || 'No response received.', bookCards);

            // Unread badge when window is closed
            if (!isOpen) {
                unreadCount++;
                unreadBadge.classList.add('visible');
            }

        } catch (err) {
            hideTyping();
            addMessage('error', '⚠️ Could not reach the server. Please check your connection.');
        } finally {
            isTyping = false;
            sendBtn.disabled = false;
            inputEl.focus();
        }
    }

    // ── Auto-resize textarea ─────────────────────────────────────────────
    function autoResizeInput() {
        inputEl.style.height = 'auto';
        inputEl.style.height = Math.min(inputEl.scrollHeight, 100) + 'px';
    }

    // ── Build suggestions bar ────────────────────────────────────────────
    function buildSuggestions() {
        suggestionsBar.innerHTML = '';
        const limited = SUGGESTIONS.slice(0, 4);
        limited.forEach(q => {
            const btn = document.createElement('button');
            btn.className = 'cb-suggestion-btn';
            btn.type = 'button';
            btn.textContent = q;
            btn.addEventListener('click', () => {
                inputEl.value = q;
                sendMessage();
            });
            suggestionsBar.appendChild(btn);
        });
    }

    // ── Welcome message ───────────────────────────────────────────────────
    function showWelcome() {
        addMessage(
            'assistant',
            'Hi! I\'m your Library Assistant. Ask me anything about our book collection — search by title, author, category, or ISBN.'
        );
    }

    // ── Check AI status ───────────────────────────────────────────────────
    async function checkStatus() {
        try {
            const resp = await fetch(STATUS_API);
            if (resp.ok) {
                const data = await resp.json();
                aiEnabled = data.ai_enabled || false;
            }
        } catch (_) {
            aiEnabled = false;
        }
    }

    // ── Keyboard shortcuts ────────────────────────────────────────────────
    function handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    }

    // ── Escape closes window ──────────────────────────────────────────────
    function handleGlobalKey(e) {
        if (e.key === 'Escape' && isOpen) toggleWindow();
    }

    // ── Build widget HTML (injected once by the Jinja template) ───────────
    // (DOM already present in chatbot_widget.html; this script wires it up)

    // ── Initialise ────────────────────────────────────────────────────────
    function init() {
        toggleBtn     = document.getElementById('chatbot-toggle-btn');
        unreadBadge   = document.getElementById('chatbot-unread-badge');
        chatWindow    = document.getElementById('chatbot-window');
        messagesArea  = document.getElementById('chatbot-messages');
        inputEl       = document.getElementById('chatbot-input');
        sendBtn       = document.getElementById('chatbot-send-btn');
        suggestionsBar = document.getElementById('chatbot-suggestions');

        if (!toggleBtn || !chatWindow) return;  // widget not on this page

        buildSuggestions();
        showWelcome();
        checkStatus();

        // Events
        toggleBtn.addEventListener('click', toggleWindow);
        sendBtn.addEventListener('click', sendMessage);
        inputEl.addEventListener('keydown', handleKeyDown);
        inputEl.addEventListener('input', autoResizeInput);
        document.addEventListener('keydown', handleGlobalKey);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
