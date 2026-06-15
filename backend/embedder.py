"""
Embedding and Vector Store
Google Gemini embeddings (gemini-embedding-001, 3072-dim) + Qdrant in-memory
"""
import logging
import itertools
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
)
from google import genai
from google.genai import types as genai_types

from config import (
    GOOGLE_API_KEY, EMBEDDING_MODEL,
    QDRANT_COLLECTION, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K_CHUNKS
)
from models import PageData, Citation

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 3072

_client: Optional[QdrantClient] = None
_genai_client: Optional[genai.Client] = None
_id_counter = itertools.count(1)


def get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=GOOGLE_API_KEY)
    return _genai_client


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(":memory:")
        _ensure_collection()
    return _client


def _ensure_collection():
    client = _client
    existing = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection '{QDRANT_COLLECTION}' ({EMBEDDING_DIM}-dim)")


def _embed_text(text: str) -> Optional[List[float]]:
    try:
        result = get_genai_client().models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=genai_types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        return list(result.embeddings[0].values)
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return None


def _embed_query(text: str) -> Optional[List[float]]:
    try:
        result = get_genai_client().models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=genai_types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return list(result.embeddings[0].values)
    except Exception as e:
        logger.error(f"Query embedding error: {e}")
        return None


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping character chunks."""
    if not text.strip():
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += chunk_size - overlap
    return chunks


def index_document(doc_id: str, doc_name: str, pages: List[PageData]) -> int:
    """Embed and index all pages. Returns number of chunks indexed."""
    client = get_client()
    points = []

    for page in pages:
        if not page.text.strip():
            continue
        for chunk_idx, chunk in enumerate(_chunk_text(page.text)):
            embedding = _embed_text(chunk)
            if embedding is None:
                continue
            points.append(PointStruct(
                id=next(_id_counter),
                vector=embedding,
                payload={
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "page_num": page.page_num,
                    "image_path": page.image_path or "",
                    "chunk_text": chunk,
                    "chunk_idx": chunk_idx,
                    "has_tables": page.has_tables,
                },
            ))

    if points:
        for i in range(0, len(points), 50):
            client.upsert(collection_name=QDRANT_COLLECTION, points=points[i:i + 50])
        logger.info(f"Indexed {len(points)} chunks for '{doc_name}'")

    return len(points)


def search_documents(query: str, top_k: int = TOP_K_CHUNKS) -> List[Citation]:
    """Search the vector store by semantic similarity. Returns ranked Citations."""
    client = get_client()
    query_vector = _embed_query(query)

    if query_vector is None:
        return []

    try:
        result = client.query_points(
            collection_name=QDRANT_COLLECTION,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )
        hits = result.points
    except AttributeError:
        try:
            hits = client.search(
                collection_name=QDRANT_COLLECTION,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True,
            )
        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
            return []
    except Exception as e:
        logger.error(f"Qdrant query error: {e}")
        return []

    return [
        Citation(
            doc_id=p.payload["doc_id"],
            doc_name=p.payload["doc_name"],
            page_num=p.payload["page_num"],
            image_path=p.payload.get("image_path", ""),
            chunk_text=p.payload["chunk_text"],
            score=p.score,
        )
        for p in hits
    ]


def delete_document(doc_id: str):
    try:
        get_client().delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
        )
        logger.info(f"Deleted vectors for doc {doc_id}")
    except Exception as e:
        logger.error(f"Delete error: {e}")


def get_document_count() -> int:
    try:
        return get_client().get_collection(QDRANT_COLLECTION).points_count or 0
    except Exception:
        return 0
