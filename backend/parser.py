"""
Document Parser
Handles: scanned PDFs, handwritten pages, image PDFs, tables, plain text
"""
import os
import io
import logging
from pathlib import Path
from typing import List, Optional

from PIL import Image
import pypdf

from config import IMAGE_DIR
from models import PageData

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import pytesseract
    import shutil
    tess_path = shutil.which("tesseract")
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path
    else:
        for candidate in [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]:
            if os.path.exists(candidate):
                pytesseract.pytesseract.tesseract_cmd = candidate
                break
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    from pdf2image import convert_from_bytes
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False


def _render_page_with_pypdf(pdf_bytes: bytes, page_num: int, doc_id: str) -> str:
    """Render a PDF page to image using pypdf. Returns relative image path."""
    image_filename = f"{doc_id}_page_{page_num}.png"
    image_path = IMAGE_DIR / image_filename

    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        if page_num - 1 < len(reader.pages):
            page = reader.pages[page_num - 1]
            images = list(page.images)
            if images:
                img_data = images[0].data
                img = Image.open(io.BytesIO(img_data))
                img.save(str(image_path))
                return f"images/{image_filename}"
    except Exception as e:
        logger.error(f"pypdf image extraction failed for page {page_num}: {e}")

    img = Image.new("RGB", (800, 1100), color=(255, 255, 255))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.text((350, 500), f"Page {page_num}", fill=(100, 100, 100))
    draw.text((200, 550), "(Install Poppler for full PDF rendering)", fill=(150, 150, 150))
    img.save(str(image_path))
    return f"images/{image_filename}"


def _render_pages_with_pdf2image(pdf_bytes: bytes, doc_id: str) -> List[str]:
    """Render all PDF pages to images using pdf2image. Returns list of relative paths."""
    paths = []
    try:
        images = convert_from_bytes(pdf_bytes, dpi=150, fmt="png")
        for i, img in enumerate(images, 1):
            filename = f"{doc_id}_page_{i}.png"
            img_path = IMAGE_DIR / filename
            img.save(str(img_path))
            paths.append(f"images/{filename}")
    except Exception as e:
        logger.error(f"pdf2image conversion failed: {e}")
    return paths


def _extract_tables_pdfplumber(plumber_page) -> Optional[str]:
    """Extract tables from a pdfplumber page as Markdown."""
    try:
        tables = plumber_page.extract_tables()
        if not tables:
            return None
        md_tables = []
        for table in tables:
            if not table or not table[0]:
                continue
            header = table[0]
            rows = table[1:]
            md = "| " + " | ".join(str(c or "") for c in header) + " |\n"
            md += "| " + " | ".join("---" for _ in header) + " |\n"
            for row in rows:
                md += "| " + " | ".join(str(c or "") for c in row) + " |\n"
            md_tables.append(md)
        return "\n\n".join(md_tables) if md_tables else None
    except Exception as e:
        logger.error(f"Table extraction error: {e}")
        return None


def _ocr_image(img: Image.Image) -> str:
    """Run Tesseract OCR on a PIL Image."""
    if not HAS_TESSERACT:
        return ""
    try:
        return pytesseract.image_to_string(img, lang="eng").strip()
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return ""


def parse_pdf(pdf_bytes: bytes, doc_id: str, original_filename: str) -> List[PageData]:
    """
    Parse a PDF document. Strategy:
    1. Render page images (pdf2image if available, else pypdf fallback)
    2. Extract native text via pdfplumber
    3. Extract tables as Markdown
    4. OCR fallback for image/scanned pages with sparse text
    """
    pages: List[PageData] = []
    image_paths = []

    if HAS_PDF2IMAGE:
        image_paths = _render_pages_with_pdf2image(pdf_bytes, doc_id)

    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for i, plumber_page in enumerate(pdf.pages, 1):
                    text = plumber_page.extract_text() or ""
                    table_md = _extract_tables_pdfplumber(plumber_page)
                    has_tables = table_md is not None

                    if len(text.strip()) < 50:
                        if image_paths and i <= len(image_paths):
                            img_full_path = IMAGE_DIR.parent / image_paths[i - 1]
                            if img_full_path.exists():
                                img = Image.open(str(img_full_path))
                                ocr_text = _ocr_image(img)
                                if len(ocr_text) > len(text):
                                    text = ocr_text
                        elif HAS_TESSERACT:
                            try:
                                page_img = plumber_page.to_image(resolution=150).original
                                ocr_text = _ocr_image(page_img)
                                if len(ocr_text) > len(text):
                                    text = ocr_text
                            except Exception:
                                pass

                    if table_md:
                        text = text + "\n\n[TABLE DATA]\n" + table_md

                    img_path = (
                        image_paths[i - 1]
                        if i <= len(image_paths)
                        else _render_page_with_pypdf(pdf_bytes, i, doc_id)
                    )

                    pages.append(PageData(
                        page_num=i,
                        text=text.strip(),
                        image_path=img_path,
                        has_tables=has_tables,
                        table_data=table_md,
                        word_count=len(text.split()),
                    ))
            return pages
        except Exception as e:
            logger.error(f"pdfplumber parsing failed: {e}")

    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        for i, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""

            if len(text.strip()) < 50 and HAS_TESSERACT and i <= len(image_paths):
                img_full_path = IMAGE_DIR.parent / image_paths[i - 1]
                if img_full_path.exists():
                    img = Image.open(str(img_full_path))
                    ocr_text = _ocr_image(img)
                    if len(ocr_text) > len(text):
                        text = ocr_text

            img_path = (
                image_paths[i - 1]
                if i <= len(image_paths)
                else _render_page_with_pypdf(pdf_bytes, i, doc_id)
            )

            pages.append(PageData(
                page_num=i,
                text=text.strip(),
                image_path=img_path,
                has_tables=False,
                word_count=len(text.split()),
            ))
    except Exception as e:
        logger.error(f"pypdf parsing failed: {e}")
        raise

    return pages


def parse_image(image_bytes: bytes, doc_id: str, mime_type: str) -> List[PageData]:
    """Parse a standalone image file using OCR."""
    image_filename = f"{doc_id}_page_1.png"
    image_path = IMAGE_DIR / image_filename

    img = Image.open(io.BytesIO(image_bytes))
    img.save(str(image_path))
    text = _ocr_image(img) if HAS_TESSERACT else "(OCR not available — install pytesseract)"

    return [PageData(
        page_num=1,
        text=text,
        image_path=f"images/{image_filename}",
        has_tables=False,
        word_count=len(text.split()),
    )]


def parse_text(text_bytes: bytes, doc_id: str) -> List[PageData]:
    """Parse a plain text file, split into 50-line page chunks."""
    text = text_bytes.decode("utf-8", errors="replace")
    lines = text.splitlines()
    page_size = 50
    pages = []
    chunks = [lines[i:i + page_size] for i in range(0, max(len(lines), 1), page_size)]

    for i, chunk in enumerate(chunks, 1):
        page_text = "\n".join(chunk)
        image_filename = f"{doc_id}_page_{i}.png"
        image_path = IMAGE_DIR / image_filename
        img = Image.new("RGB", (800, 1100), color=(250, 250, 250))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), f"Page {i}", fill=(50, 50, 50))
        y = 50
        for line in chunk[:40]:
            if y > 1050:
                break
            draw.text((20, y), line[:100], fill=(30, 30, 30))
            y += 20
        img.save(str(image_path))

        pages.append(PageData(
            page_num=i,
            text=page_text,
            image_path=f"images/{image_filename}",
            has_tables=False,
            word_count=len(page_text.split()),
        ))

    return pages or [PageData(page_num=1, text="(empty document)", image_path="", has_tables=False)]


def parse_document(file_bytes: bytes, doc_id: str, original_filename: str, mime_type: str) -> List[PageData]:
    """Unified entry point — routes to the correct parser by MIME type."""
    ext = Path(original_filename).suffix.lower()

    if mime_type == "application/pdf" or ext == ".pdf":
        return parse_pdf(file_bytes, doc_id, original_filename)
    elif mime_type in ("image/png", "image/jpeg") or ext in (".png", ".jpg", ".jpeg"):
        return parse_image(file_bytes, doc_id, mime_type)
    elif mime_type == "text/plain" or ext == ".txt":
        return parse_text(file_bytes, doc_id)
    else:
        raise ValueError(f"Unsupported file type: {mime_type} / {ext}")
