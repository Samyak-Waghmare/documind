"""
FastAPI Main Application
Document Intelligence + Agentic RAG Backend
"""
import json
import logging
import asyncio
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI, UploadFile, File, HTTPException,
    Depends, BackgroundTasks, Header, Request
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

from config import (
    UPLOAD_DIR, IMAGE_DIR, SAMPLE_DOCS_DIR,
    ALLOWED_ORIGINS, INTERNAL_API_KEY
)
from models import (
    DocumentRecord, DocumentClassification,
    ChatRequest, ChatResponse, Citation,
    UploadResponse, StatusUpdate, ChatMessage
)
from security import validate_upload, sanitize_filename, generate_safe_doc_id, compute_file_hash, verify_api_key
from parser import parse_document
from classifier import classify_document
from embedder import index_document, get_document_count, get_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# App + Lifespan
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_event()
    yield


app = FastAPI(
    title="Document Intelligence API",
    description="Agentic RAG with document parsing, classification and grounded citations",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(IMAGE_DIR.parent)), name="uploads")

_documents: dict[str, DocumentRecord] = {}
_sse_queues: dict[str, asyncio.Queue] = {}


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────

def get_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")
    return x_api_key


# ─────────────────────────────────────────────
# Health / Info
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "indexed_chunks": get_document_count()}


@app.get("/documents")
async def list_documents():
    return list(_documents.values())


@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    if doc_id not in _documents:
        raise HTTPException(404, "Document not found")
    return _documents[doc_id]


# ─────────────────────────────────────────────
# Upload & Processing
# ─────────────────────────────────────────────

@app.post("/upload", response_model=List[UploadResponse])
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    api_key: str = Depends(get_api_key),
):
    """Upload multiple documents. Returns doc IDs immediately; processing is async."""
    responses = []
    for file in files:
        doc_id = generate_safe_doc_id()
        safe_name = sanitize_filename(file.filename or "unknown.pdf")

        try:
            content = await validate_upload(file)
        except HTTPException as e:
            responses.append(UploadResponse(
                doc_id=doc_id, filename=safe_name,
                status="error", message=str(e.detail),
            ))
            continue

        stored_path = UPLOAD_DIR / f"{doc_id}_{safe_name}"
        stored_path.write_bytes(content)

        record = DocumentRecord(
            doc_id=doc_id,
            original_filename=safe_name,
            stored_filename=str(stored_path),
            upload_time=datetime.utcnow().isoformat(),
            num_pages=0,
            status="pending",
        )
        _documents[doc_id] = record

        from security import _detect_mime
        mime = _detect_mime(content, safe_name)

        background_tasks.add_task(
            process_document_pipeline,
            doc_id=doc_id, content=content,
            safe_name=safe_name, mime=mime,
        )

        responses.append(UploadResponse(
            doc_id=doc_id, filename=safe_name,
            status="pending", message="Processing started",
        ))

    return responses


async def process_document_pipeline(doc_id: str, content: bytes, safe_name: str, mime: str):
    """Background task: parse → classify (LLM) → embed + index."""
    record = _documents.get(doc_id)
    if not record:
        return

    async def emit(status: str, progress: int, message: str, classification=None, error=None):
        record.status = status
        update = StatusUpdate(
            doc_id=doc_id, filename=safe_name,
            status=status, progress=progress, message=message,
            classification=classification, error=error,
        )
        for q in list(_sse_queues.values()):
            try:
                q.put_nowait(update)
            except asyncio.QueueFull:
                pass

    try:
        await emit("parsing", 10, "Parsing document...")
        loop = asyncio.get_running_loop()
        pages = await loop.run_in_executor(
            None, parse_document, content, doc_id, safe_name, mime
        )
        record.num_pages = len(pages)
        await emit("classifying", 40, f"Parsed {len(pages)} pages. Classifying with LLM...")

        classification = await loop.run_in_executor(
            None, classify_document, pages, safe_name
        )
        record.classification = classification
        await emit("indexing", 70, "Embedding and indexing...", classification=classification)

        num_chunks = await loop.run_in_executor(
            None, index_document, doc_id, safe_name, pages
        )
        record.status = "indexed"
        await emit("indexed", 100, f"Done! {num_chunks} chunks indexed.", classification=classification)

    except Exception as e:
        logger.exception(f"Pipeline error for {doc_id}: {e}")
        record.status = "error"
        record.error_message = str(e)
        await emit("error", 0, f"Processing failed: {e}", error=str(e))


@app.get("/upload/events")
async def upload_events(request: Request):
    """SSE endpoint for real-time upload progress."""
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _sse_queues[session_id] = queue

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {update.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    yield "data: {\"type\": \"ping\"}\n\n"
        finally:
            _sse_queues.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─────────────────────────────────────────────
# Chat / RAG  (strict LLM — no offline fallback)
# ─────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, api_key: str = Depends(get_api_key)):
    """RAG chat endpoint. Returns LLM answer with grounded citations."""
    from agent import answer_question

    if not request.message.strip():
        raise HTTPException(400, "Message cannot be empty")

    message = request.message[:2000]
    session_id = request.session_id or str(uuid.uuid4())

    try:
        answer, citations = answer_question(message, request.history)
    except Exception as e:
        logger.error(f"Chat LLM error: {e}")
        raise HTTPException(status_code=502, detail=f"LLM unavailable: {str(e)[:200]}")

    return ChatResponse(
        answer=answer,
        citations=citations,
        session_id=session_id,
    )


# ─────────────────────────────────────────────
# Delete Document
# ─────────────────────────────────────────────

@app.delete("/documents/{doc_id}")
async def delete_document_endpoint(doc_id: str, api_key: str = Depends(get_api_key)):
    """Remove a document from the knowledge base."""
    if doc_id not in _documents:
        raise HTTPException(404, "Document not found")
    from embedder import delete_document
    delete_document(doc_id)
    del _documents[doc_id]
    return {"status": "deleted", "doc_id": doc_id}


# ─────────────────────────────────────────────
# Startup: Index sample documents
# ─────────────────────────────────────────────

async def startup_event():
    """Index sample documents on first run (staggered to avoid rate limits)."""
    logger.info("Starting Document Intelligence API...")

    try:
        get_client()
    except Exception as e:
        logger.error(f"Vector store init error: {e}")

    if SAMPLE_DOCS_DIR.exists():
        sample_files = (
            list(SAMPLE_DOCS_DIR.glob("*.pdf"))
            + list(SAMPLE_DOCS_DIR.glob("*.txt"))
            + list(SAMPLE_DOCS_DIR.glob("*.png"))
        )

        for sample_file in sample_files:
            already = any(
                r.original_filename == sample_file.name
                for r in _documents.values()
            )
            if already:
                continue

            logger.info(f"Queuing sample doc: {sample_file.name}")
            content = sample_file.read_bytes()
            doc_id = generate_safe_doc_id()

            from security import _detect_mime
            mime = _detect_mime(content, sample_file.name)

            record = DocumentRecord(
                doc_id=doc_id,
                original_filename=sample_file.name,
                stored_filename=str(sample_file),
                upload_time=datetime.utcnow().isoformat(),
                num_pages=0,
                status="pending",
            )
            _documents[doc_id] = record

            # Stagger 25s between docs to stay within free-tier rate limits (15 RPM)
            await asyncio.sleep(25)
            asyncio.create_task(process_document_pipeline(
                doc_id=doc_id, content=content,
                safe_name=sample_file.name, mime=mime,
            ))

    logger.info("API startup complete.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
