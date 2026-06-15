"""
Document Classifier using Google Gemini LLM (new google.genai SDK)
"""
import json
import logging
import time
from typing import List

from google import genai
from google.genai import types as genai_types

from config import GOOGLE_API_KEY, GEMINI_MODEL
from models import DocumentClassification, PageData

logger = logging.getLogger(__name__)

_client = None

def get_genai_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client


CLASSIFICATION_PROMPT = """You are a document intelligence system. Analyze the following document text and classify it.

Return ONLY a valid JSON object with this exact schema (no markdown, no extra text):
{{
  "document_type": "<one of: invoice, report, contract, letter, handwritten, academic, technical, medical, legal, financial, news, other>",
  "topic": "<main topic/subject in 5-10 words>",
  "language": "<primary language, e.g., English>",
  "sensitivity_level": "<one of: public, internal, confidential, strictly_confidential>",
  "has_tables": <true or false>,
  "has_handwriting": <true or false>,
  "has_images": <true or false>,
  "summary": "<2-3 sentence summary of the document>",
  "key_entities": ["<named entity 1>", "<named entity 2>"],
  "content_characteristics": ["<tag1>", "<tag2>"]
}}

Sensitivity level guide:
- public: No sensitive data, can be shared freely
- internal: Internal business info, not for public
- confidential: Personal data, financial data, NDA-level info
- strictly_confidential: Medical records, legal proceedings, passwords, SSNs

Document text (first 3000 chars):
{text}

Filename: {filename}
Total pages: {num_pages}
"""


def classify_document(
    pages: List[PageData],
    filename: str,
) -> DocumentClassification:
    """
    Classify a document using Gemini LLM.
    Retries up to 3 times on 429/503. Raises on all other errors.
    """
    combined_text = ""
    for page in pages[:5]:
        combined_text += f"\n--- Page {page.page_num} ---\n{page.text}"
    combined_text = combined_text[:3000]

    has_tables = any(p.has_tables for p in pages)

    prompt = CLASSIFICATION_PROMPT.format(
        text=combined_text,
        filename=filename,
        num_pages=len(pages),
    )

    wait = 10
    raw = ""
    for attempt in range(3):
        try:
            response = get_genai_client().models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1024,
                ),
            )
            raw = response.text.strip()
            break
        except Exception as e:
            err = str(e)
            if ("429" in err or "RESOURCE_EXHAUSTED" in err or
                    "503" in err or "UNAVAILABLE" in err) and attempt < 2:
                logger.warning(f"Rate limit on classify '{filename}' — retry in {wait}s")
                time.sleep(wait)
                wait *= 2
            else:
                raise  # propagate — no offline fallback

    # Strip markdown fences if model wraps response
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        data = json.loads(raw)  # raises JSONDecodeError if malformed
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}. Raw: {raw[:100]}")
        data = {
            "document_type": "other",
            "topic": "Unknown Document",
            "language": "Unknown",
            "sensitivity_level": "public",
            "has_tables": False,
            "has_handwriting": False,
            "has_images": False,
            "summary": "AI classification failed due to parsing error.",
            "key_entities": [],
            "content_characteristics": []
        }

    if has_tables:
        data["has_tables"] = True

    return DocumentClassification(**data)
