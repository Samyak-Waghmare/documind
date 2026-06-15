from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PageData(BaseModel):
    page_num: int
    text: str
    image_path: str
    has_tables: bool = False
    table_data: Optional[str] = None
    word_count: int = 0


class DocumentClassification(BaseModel):
    document_type: str
    topic: str
    language: str
    sensitivity_level: str
    has_tables: bool
    has_handwriting: bool
    has_images: bool
    summary: str
    key_entities: List[str]
    content_characteristics: List[str]


class DocumentRecord(BaseModel):
    doc_id: str
    original_filename: str
    stored_filename: str
    upload_time: str
    num_pages: int
    classification: Optional[DocumentClassification] = None
    status: str = "pending"
    error_message: Optional[str] = None


class Citation(BaseModel):
    doc_id: str
    doc_name: str
    page_num: int
    image_path: str
    chunk_text: str
    score: float = 0.0


class ChatMessage(BaseModel):
    role: str
    content: str
    citations: Optional[List[Citation]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    session_id: str


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    status: str
    message: str


class StatusUpdate(BaseModel):
    doc_id: str
    filename: str
    status: str
    progress: int
    message: str
    classification: Optional[DocumentClassification] = None
    error: Optional[str] = None
