import os
import re
import uuid
from werkzeug.utils import secure_filename

# Allowed file extensions categorized by workflow
TABULAR_EXTENSIONS = {'csv', 'xlsx', 'xls'}
DOCUMENT_EXTENSIONS = {'pdf', 'docx', 'doc'}
ALL_ALLOWED_EXTENSIONS = TABULAR_EXTENSIONS | DOCUMENT_EXTENSIONS

# File signatures (magic bytes) for real file-type verification
MAGIC_SIGNATURES = {
    'pdf': [b'%PDF-'],
    'docx': [b'PK\x03\x04'],
    'xlsx': [b'PK\x03\x04'],
    'doc': [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],
    'xls': [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],
}

MAX_DEFAULT_SIZE_BYTES = 16 * 1024 * 1024  # 16 MB

class FileValidationError(Exception):
    """Custom exception raised for security or format validation failures."""
    pass

def get_file_extension(filename: str) -> str:
    """Extract lowercase file extension without leading dot."""
    if not filename or '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower().strip()

def sanitize_original_filename(filename: str) -> str:
    """Sanitize original filename for display and metadata storage."""
    base = os.path.basename(filename.replace('\\', '/'))
    cleaned = secure_filename(base)
    if not cleaned:
        cleaned = f"file_{uuid.uuid4().hex[:8]}"
    return cleaned

def generate_stored_filename(original_filename: str) -> tuple[str, str]:
    """
    Generate a collision-proof, path-traversal-proof filename.
    Returns (stored_filename, extension).
    """
    ext = get_file_extension(original_filename)
    if ext not in ALL_ALLOWED_EXTENSIONS:
        raise FileValidationError(f"Unsupported file extension '.{ext}'. Supported extensions: {', '.join(sorted(ALL_ALLOWED_EXTENSIONS))}")

    safe_uid = uuid.uuid4().hex
    safe_base = secure_filename(original_filename.rsplit('.', 1)[0])[:30]
    safe_base = re.sub(r'[^a-zA-Z0-9_-]', '_', safe_base)
    if not safe_base:
        safe_base = "doc"

    stored_name = f"{safe_base}_{safe_uid}.{ext}"
    return stored_name, ext

def validate_uploaded_file(file_storage, allowed_extensions=None, max_bytes=None) -> tuple[str, int]:
    """
    Validate uploaded file:
    1. Presence of file
    2. Extension whitelist
    3. Maximum file size
    4. Magic bytes / header inspection (to prevent executable spoofing)
    
    Returns (normalized_extension, file_size_in_bytes).
    """
    if allowed_extensions is None:
        allowed_extensions = ALL_ALLOWED_EXTENSIONS
    if max_bytes is None:
        max_bytes = int(os.environ.get('MAX_UPLOAD_SIZE_BYTES', MAX_DEFAULT_SIZE_BYTES))

    if not file_storage or not file_storage.filename:
        raise FileValidationError("No file selected for upload.")

    filename = file_storage.filename
    ext = get_file_extension(filename)

    if ext not in allowed_extensions:
        formatted = ", ".join(f".{e}" for e in sorted(allowed_extensions))
        raise FileValidationError(f"Invalid file type '.{ext}'. Allowed types for this action: {formatted}")

    # Read initial bytes to check size and file signature
    stream = file_storage.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)

    if size == 0:
        raise FileValidationError("The uploaded file is empty (0 bytes).")

    if size > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        raise FileValidationError(f"File size ({size / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of {max_mb:.0f} MB.")

    # Inspect file header signature
    header = stream.read(1024)
    stream.seek(0)

    if ext in MAGIC_SIGNATURES:
        valid_signatures = MAGIC_SIGNATURES[ext]
        matched = any(header.startswith(sig) for sig in valid_signatures)
        if not matched:
            raise FileValidationError(f"File content does not match genuine .{ext} file signature. Upload rejected for security.")

    elif ext == 'csv':
        # Verify CSV is legitimate text and does not contain binary NULL bytes (e.g. disguised executables)
        if b'\x00' in header:
            raise FileValidationError("CSV file contains invalid binary content or null bytes.")
        try:
            # Check text decodability
            header.decode('utf-8')
        except UnicodeDecodeError:
            try:
                header.decode('latin-1')
            except Exception:
                raise FileValidationError("CSV file cannot be decoded as valid text (UTF-8 or Latin-1 required).")

    return ext, size
