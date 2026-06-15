"""
Security — file validation, API key auth, filename sanitization
"""
import re
import uuid
import hashlib
import logging
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from fastapi.security import APIKeyHeader

from config import MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS, ALLOWED_MIMETYPES, INTERNAL_API_KEY

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: Optional[str]) -> bool:
    """Constant-time API key comparison (timing-attack safe)."""
    if not api_key:
        return False
    return hmac_compare(api_key, INTERNAL_API_KEY)


def hmac_compare(a: str, b: str) -> bool:
    import hmac
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def require_api_key(api_key: Optional[str] = None):
    if not verify_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key. Set X-API-Key header.")


def sanitize_filename(filename: str) -> str:
    """Strip path traversal and special characters. Returns a safe filename."""
    name = Path(filename).name
    safe = re.sub(r"[^\w\-_\. ]", "_", name)
    if len(safe) > 100:
        ext = Path(safe).suffix
        safe = safe[:90] + ext
    return safe


def generate_safe_doc_id() -> str:
    return str(uuid.uuid4())


async def validate_upload(file: UploadFile) -> bytes:
    """
    Validate uploaded file: extension whitelist, size limit, MIME magic-byte check.
    Returns file bytes if valid, raises HTTPException otherwise.
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {ALLOWED_EXTENSIONS}",
        )

    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    content = b""
    chunk_size = 64 * 1024

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        content += chunk
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB",
            )

    detected_mime = _detect_mime(content, file.filename or "")
    if detected_mime not in ALLOWED_MIMETYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Detected MIME type '{detected_mime}' not allowed.",
        )

    return content


def _detect_mime(content: bytes, filename: str) -> str:
    """Detect MIME type from magic bytes via filetype library."""
    try:
        import filetype as ft
        kind = ft.guess(content)
        if kind:
            return kind.mime
    except Exception:
        pass

    ext = Path(filename).suffix.lower()
    mapping = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".txt": "text/plain",
    }
    return mapping.get(ext, "application/octet-stream")


def compute_file_hash(content: bytes) -> str:
    """SHA-256 hash of file content for integrity tracking."""
    return hashlib.sha256(content).hexdigest()
