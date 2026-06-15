import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

UPLOAD_DIR = BASE_DIR / "uploads" / "docs"
IMAGE_DIR = BASE_DIR / "uploads" / "images"
QDRANT_PATH = BASE_DIR / "qdrant_storage"
SAMPLE_DOCS_DIR = BASE_DIR / "sample_docs"

for d in [UPLOAD_DIR, IMAGE_DIR, QDRANT_PATH]:
    d.mkdir(parents=True, exist_ok=True)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}
ALLOWED_MIMETYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
}

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")

QDRANT_COLLECTION = "documents"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
TOP_K_CHUNKS = 6

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
