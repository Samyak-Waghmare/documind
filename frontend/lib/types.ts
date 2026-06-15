export interface Citation {
  doc_id: string
  doc_name: string
  page_num: number
  image_path: string
  chunk_text: string
  score: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  timestamp?: string
}

export interface DocumentClassification {
  document_type: string
  topic: string
  language: string
  sensitivity_level: 'public' | 'internal' | 'confidential' | 'strictly_confidential'
  has_tables: boolean
  has_handwriting: boolean
  has_images: boolean
  summary: string
  key_entities: string[]
  content_characteristics: string[]
}

export interface DocumentRecord {
  doc_id: string
  original_filename: string
  stored_filename: string
  upload_time: string
  num_pages: number
  classification?: DocumentClassification
  status: 'pending' | 'parsing' | 'classifying' | 'indexing' | 'indexed' | 'error'
  error_message?: string
}

export interface StatusUpdate {
  doc_id: string
  filename: string
  status: string
  progress: number
  message: string
  classification?: DocumentClassification
  error?: string
}

export interface ChatResponse {
  answer: string
  citations: Citation[]
  session_id: string
}
