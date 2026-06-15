# DocuMind — Document Intelligence + Agentic RAG

> **AI Engineer Intern Assessment** · Build Fast with AI

A production-ready web application that ingests messy, real-world documents (scanned PDFs, handwritten pages, image-heavy reports, tables, unstructured files), extracts content accurately, classifies each document using LLM, and powers a chatbot that answers questions with **grounded citations** showing the exact source page.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js 14)                   │
│                                                             │
│  /          → Chatbot with voice input + citation chips     │
│  /upload    → Bulk upload with SSE real-time progress       │
│  /documents → Knowledge base browser                        │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP + SSE
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI + Python 3.12)            │
│                                                             │
│  POST /upload     → Validate + parse + classify + index     │
│  GET  /upload/events → SSE stream for progress updates      │
│  POST /chat       → RAG answer with citations               │
│  GET  /documents  → List indexed docs                       │
│  GET  /uploads/*  → Static file serving (page images)      │
└─────┬──────────────┬────────────────┬───────────────────────┘
      │              │                │
      ▼              ▼                ▼
 parser.py    classifier.py     embedder.py
 (pdfplumber  (Gemini LLM)     (Qdrant local
  pytesseract                   + Gemini
  pdf2image)                    embeddings)
                                      │
                                      ▼
                               agent.py (RAG)
                               (Gemini LLM)
```

## ✨ Features

| Feature | Implementation |
|---|---|
| **PDF Parsing** | pdfplumber (native text), pytesseract OCR (scanned), pdf2image (page rendering) |
| **Table Extraction** | pdfplumber structured table → Markdown format |
| **OCR** | pytesseract fallback for image-heavy/handwritten pages |
| **Classification** | Gemini LLM → structured JSON across 10 dimensions |
| **Vector Search** | Qdrant (in-memory) + Gemini `gemini-embedding-001` (3072-dim) |
| **Agentic RAG** | Gemini LLM with retrieval tools, hallucination guard |
| **Citations** | Inline [doc, Page N] with thumbnail images |
| **Bulk Upload** | Drag-and-drop, multi-file, SSE real-time progress |
| **Voice Input** | Web Speech API (browser-native, no API key needed) |
| **Security** | API key auth, MIME validation, UUID filenames, CORS |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12
- Node.js 18+
- Google Gemini API key (free tier: [aistudio.google.com](https://aistudio.google.com/app/apikey))
- (Optional) Tesseract OCR for scanned docs
- (Optional) Poppler for high-quality PDF rendering

### 1. Backend Setup

```bash
cd backend

# Copy environment template and fill in your keys
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# Start the backend server
python main.py
```

**Sample documents** are automatically indexed on first startup from `backend/sample_docs/`.

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy and configure environment
# Set NEXT_PUBLIC_API_URL to your backend URL
cp .env.local.example .env.local

# Start the frontend
npm run dev
```

---

## 📁 Project Structure

```
documind/
├── backend/
│   ├── main.py              # FastAPI application + all routes
│   ├── parser.py            # Document parsing (PDF/OCR/image/text)
│   ├── classifier.py        # LLM document classification
│   ├── embedder.py          # Gemini embeddings + Qdrant vector store
│   ├── agent.py             # Agentic RAG answer synthesis
│   ├── security.py          # Auth, validation, sanitization
│   ├── models.py            # Pydantic data models
│   ├── config.py            # Configuration / env loading
│   ├── sample_docs/         # 7 sample documents (auto-indexed on startup)
│   ├── uploads/
│   │   ├── docs/            # Stored documents (UUID-named)
│   │   └── images/          # Rendered page images
│   ├── qdrant_storage/      # Qdrant vector store (in-memory, auto-recreated)
│   ├── .env                 # Environment variables (not in git)
│   └── .env.example         # Environment template
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx       # Root layout with sidebar
│   │   ├── page.tsx         # Chatbot page (/)
│   │   ├── upload/page.tsx  # Bulk upload (/upload)
│   │   ├── documents/page.tsx # Knowledge base (/documents)
│   │   └── globals.css      # Full design system
│   ├── components/
│   │   ├── Sidebar.tsx      # Navigation sidebar
│   │   ├── ChatInterface.tsx # Multi-turn chat + voice input
│   │   ├── UploadPage.tsx   # Drag-drop upload + SSE progress
│   │   └── PageModal.tsx    # Page image viewer modal
│   ├── lib/
│   │   ├── api.ts           # API client with key injection
│   │   └── types.ts         # TypeScript types
│   └── .env.local           # Frontend env variables (not in git)
│
└── README.md
```

---

## 🔍 Document Classification Schema

Every document is classified into structured JSON:

```json
{
  "document_type": "financial | report | invoice | academic | medical | legal | technical | news | other",
  "topic": "Main subject in 5-10 words",
  "language": "English",
  "sensitivity_level": "public | internal | confidential | strictly_confidential",
  "has_tables": true,
  "has_handwriting": false,
  "has_images": false,
  "summary": "2-3 sentence summary",
  "key_entities": ["ACME Corp", "Robert Chen", "2024"],
  "content_characteristics": ["financial-data", "quarterly-report", "tabular"]
}
```

**Sensitivity levels**:
- `public` — No restrictions, shareable
- `internal` — Internal business info
- `confidential` — Personal data, financial data, NDAs
- `strictly_confidential` — Medical records, legal proceedings

---

## 🛡️ Security Decisions

### What I Implemented

#### Upload Layer
- **MIME type validation via magic bytes** (`filetype` library sniffs actual file content, not just extension)
- **File extension whitelist** (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.txt` only)
- **File size limit** (50MB per file, configurable via env)
- **Filename sanitization** (regex strips path traversal characters, limits length)
- **API key authentication** on all write endpoints (`X-API-Key` header)
- **Constant-time string comparison** (`hmac.compare_digest`) to prevent timing attacks

#### Storage Layer
- **UUID-based filenames** — user-supplied filenames are never used as storage paths
- **Files stored outside web root** — documents stored in `uploads/docs/`, not served directly
- **Page images served separately** — only rendered images served, not raw documents
- **No directory traversal** — filenames are sanitized before path construction

#### Processing Layer
- **Input length limits** — document text truncated before LLM processing (prevent prompt injection attacks)
- **Error isolation** — processing errors don't expose internal paths or stack traces to clients
- **Subprocess control** — pytesseract runs isolated, input validated before OCR

#### API / Retrieval Layer
- **CORS restricted** — only configured origins allowed
- **Query sanitization** — user queries capped at 2000 characters
- **No prompt injection passthrough** — system prompt separation from user query
- **Relevance thresholding** — results with cosine similarity < 0.3 filtered out
- **No secrets in code** — all secrets via `.env` file

### What I Considered But Skipped (Due to Time)
- **User authentication** — JWT-based multi-user system (currently single shared API key)
- **Document encryption at rest** — AES encryption of stored PDFs
- **Redis rate limiting** — `slowapi` is ready but not fully wired (needs Redis)
- **Audit logging** — track who accessed which document
- **Content scanning** — malware/antivirus scanning of uploads
- **Watermarking** — adding invisible watermarks to served page images

### What I Would Add with More Time
- **Full auth system**: OAuth2/JWT with per-user document isolation
- **Encryption at rest**: Documents encrypted before storage using `cryptography` library
- **PII detection**: Scan documents and auto-redact sensitive fields before display
- **Virus scanning**: ClamAV integration for malware scanning
- **mTLS**: Mutual TLS between frontend and backend in production
- **Secrets management**: HashiCorp Vault instead of `.env` files
- **CSP headers**: Content Security Policy to prevent XSS
- **Rate limiting**: Per-IP/API-key rate limits with Redis backend

---

## 🎙️ Voice Input

Voice input uses the **Web Speech API** (browser-native, no API keys, no costs):
- Supported in Chrome, Edge, Safari
- Real-time interim transcript shown as user speaks
- Final transcript appended to chat input
- Press 🎤 to start, ⏹ to stop

---

## 📦 Sample Documents (7 files)

Pre-loaded documents for immediate chatbot testing:

| File | Type | Sensitivity | Content |
|---|---|---|---|
| `financial_report_2024.pdf` | Financial | Confidential | Revenue tables, balance sheet, Q3 metrics |
| `ml_research_paper.txt` | Academic | Public | LLM fine-tuning comparison study |
| `patient_medical_report.txt` | Medical | Strictly Confidential | Patient diagnosis, lab results, treatment plan |
| `software_license_agreement.txt` | Legal | Confidential | SaaS license terms, payment, IP clauses |
| `api_technical_specification.txt` | Technical | Internal | REST API spec, endpoints, error codes |
| `tech_industry_news.txt` | News | Public | AI investment, chip news, regulation |
| `vendor_invoice_2024.txt` | Invoice | Confidential | Line items, payment details, banking info |

### Sample Questions to Try
- *"What was ACME Corporation's total revenue in 2024?"*
- *"What are the main findings of the ML research paper?"*
- *"What is the patient's diagnosis?"*
- *"What are the payment terms in the software license?"*
- *"What is the rate limit for the API Pro tier?"*

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **LLM** | Google Gemini 2.5 Flash (free tier) |
| **Embeddings** | Gemini `gemini-embedding-001` (3072-dim) |
| **Vector Store** | Qdrant (in-memory, no server needed) |
| **PDF Parsing** | pdfplumber, pypdf |
| **OCR** | pytesseract + Pillow |
| **Page Rendering** | pdf2image (requires Poppler) |
| **Frontend** | Next.js 14, TypeScript, Vanilla CSS |
| **Voice** | Web Speech API (browser-native) |
| **Security** | filetype (MIME), hmac, python-dotenv |

---

## 🌐 Deployment

### Backend → [Render.com](https://render.com)
1. New Web Service → connect your GitHub repository
2. Root Directory: `backend`
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add Environment Variables:
   - `GOOGLE_API_KEY` = your Gemini API key
   - `INTERNAL_API_KEY` = a strong random secret
   - `ALLOWED_ORIGINS` = your Vercel frontend URL
   - `GEMINI_MODEL` = `gemini-2.5-flash`
   - `EMBEDDING_MODEL` = `models/gemini-embedding-001`

### Frontend → [Vercel.com](https://vercel.com)
1. Import your GitHub repository
2. Root Directory: `frontend`
3. Add Environment Variables:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL
   - `NEXT_PUBLIC_API_KEY` = same secret as `INTERNAL_API_KEY` above

---

## 🤝 License

MIT License — Open for educational and assessment purposes.
