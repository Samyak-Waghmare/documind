"""
Agentic RAG using Google Gemini (new SDK)
"""
import logging
import time
from typing import List, Tuple

from google import genai
from google.genai import types as genai_types

from config import GOOGLE_API_KEY, GEMINI_MODEL, TOP_K_CHUNKS
from models import Citation, ChatMessage
from embedder import search_documents

logger = logging.getLogger(__name__)

_client = None

def get_genai_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client


RAG_SYSTEM_PROMPT = """You are a Document Intelligence Assistant with access to a knowledge base of uploaded documents.

Your job:
1. Answer questions using ONLY the provided document chunks.
2. Always cite your sources using [doc_name, Page N] format inline.
3. If no relevant content exists, say: "I don't have relevant information in the knowledge base to answer that question."
4. NEVER hallucinate or make up information not in the provided chunks.
5. If the question is about a sensitive document, be careful with personal data.

Format your response clearly with inline citations.
"""


def _format_chunks_for_prompt(citations: List[Citation]) -> str:
    if not citations:
        return "(No relevant documents found in the knowledge base)"
    parts = []
    for i, cite in enumerate(citations, 1):
        parts.append(
            f"[Source {i}] Document: '{cite.doc_name}', Page {cite.page_num} "
            f"(relevance: {cite.score:.2f})\n{cite.chunk_text}"
        )
    return "\n\n---\n\n".join(parts)


def _format_history(history: List[ChatMessage]) -> str:
    if not history:
        return ""
    lines = []
    for msg in history[-6:]:
        role = "User" if msg.role == "user" else "Assistant"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)


def _generate_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Call Gemini with exponential backoff. Raises on failure — no fallback."""
    wait = 15
    for attempt in range(max_retries):
        try:
            response = get_genai_client().models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=2048,
                ),
            )
            return response.text.strip()
        except Exception as e:
            err = str(e)
            if ("429" in err or "RESOURCE_EXHAUSTED" in err or
                    "503" in err or "UNAVAILABLE" in err) and attempt < max_retries - 1:
                logger.warning(f"Rate limit (attempt {attempt+1}), retrying in {wait}s...")
                time.sleep(wait)
                wait *= 2
            else:
                raise  # propagate — no offline fallback


def answer_question(
    question: str,
    history: List[ChatMessage],
    top_k: int = TOP_K_CHUNKS,
) -> Tuple[str, List[Citation]]:
    """
    RAG pipeline: retrieve → build prompt → generate with retry.
    Raises on LLM failure — caller (main.py /chat) returns HTTP 502.
    """
    # Step 1: Retrieve relevant chunks
    citations = search_documents(question, top_k=top_k)
    relevant_citations = [c for c in citations if c.score >= 0.3]

    # Step 2: Build prompt
    context = _format_chunks_for_prompt(relevant_citations)
    history_text = _format_history(history)

    prompt = f"""{RAG_SYSTEM_PROMPT}

{"Conversation History:" + chr(10) + history_text if history_text else ""}

Retrieved Document Chunks:
{context}

User Question: {question}

Answer (with inline citations in [document name, Page N] format):"""

    # Step 3: Generate — raises if LLM unavailable
    answer = _generate_with_retry(prompt)

    # Deduplicate citations by (doc_name, page_num)
    seen = {}
    for c in relevant_citations:
        key = (c.doc_name, c.page_num)
        if key not in seen or c.score > seen[key].score:
            seen[key] = c
    deduped = sorted(seen.values(), key=lambda x: -x.score)

    return answer, deduped
