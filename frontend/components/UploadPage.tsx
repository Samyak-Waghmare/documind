'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { StatusUpdate, DocumentClassification } from '@/lib/types'
import { apiFetch, API_BASE } from '@/lib/api'

interface FileState {
  file: File
  docId?: string
  status: string
  progress: number
  message: string
  classification?: DocumentClassification
  error?: string
}

function getFileIcon(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (ext === 'pdf') return '📕'
  if (ext === 'png' || ext === 'jpg' || ext === 'jpeg') return '🖼️'
  if (ext === 'txt') return '📄'
  return '📎'
}

function getFileClass(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (ext === 'pdf') return 'pdf'
  if (ext === 'png' || ext === 'jpg' || ext === 'jpeg') return 'img'
  return 'txt'
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const sensitivityColors: Record<string, string> = {
  public: 'var(--accent-success)',
  internal: 'var(--accent-warning)',
  confidential: '#f97316',
  strictly_confidential: 'var(--accent-danger)',
}

export default function UploadPage() {
  const [files, setFiles] = useState<FileState[]>([])
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    const es = new EventSource(`${API_BASE}/upload/events`)
    eventSourceRef.current = es

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'ping' || data.type === 'connected') return
        const update: StatusUpdate = data
        setFiles(prev => prev.map(f =>
          f.docId === update.doc_id
            ? {
                ...f,
                status: update.status,
                progress: update.progress,
                message: update.message,
                classification: update.classification || f.classification,
                error: update.error,
              }
            : f
        ))
      } catch {}
    }

    return () => es.close()
  }, [])

  const processFiles = useCallback((newFiles: File[]) => {
    const validFiles = newFiles.filter(f => {
      const ext = f.name.split('.').pop()?.toLowerCase()
      return ['pdf', 'png', 'jpg', 'jpeg', 'txt'].includes(ext || '')
    })

    if (validFiles.length === 0) {
      alert('No valid files selected. Allowed: PDF, PNG, JPG, TXT')
      return
    }

    setFiles(prev => [
      ...prev,
      ...validFiles.map(f => ({ file: f, status: 'pending', progress: 0, message: 'Queued for upload' })),
    ])
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    processFiles(Array.from(e.dataTransfer.files))
  }, [processFiles])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) processFiles(Array.from(e.target.files))
  }

  const uploadAll = async () => {
    const pending = files.filter(f => f.status === 'pending' && !f.docId)
    if (pending.length === 0) return

    setUploading(true)
    const formData = new FormData()
    pending.forEach(f => formData.append('files', f.file))

    try {
      const res = await apiFetch('/upload', { method: 'POST', body: formData })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed')
      }

      const results = await res.json()
      setFiles(prev => {
        const updated = [...prev]
        let idx = 0
        for (let i = 0; i < updated.length; i++) {
          if (!updated[i].docId && updated[i].status === 'pending' && idx < results.length) {
            updated[i] = {
              ...updated[i],
              docId: results[idx].doc_id,
              status: results[idx].status,
              message: results[idx].message,
              progress: 5,
            }
            idx++
          }
        }
        return updated
      })
    } catch (err: any) {
      alert(`Upload error: ${err.message}`)
    } finally {
      setUploading(false)
    }
  }

  const clearCompleted = () => {
    setFiles(prev => prev.filter(f => f.status !== 'indexed' && f.status !== 'error'))
  }

  const pendingCount = files.filter(f => f.status === 'pending' && !f.docId).length
  const indexedCount = files.filter(f => f.status === 'indexed').length
  const processingCount = files.filter(f => ['parsing', 'classifying', 'indexing'].includes(f.status)).length

  return (
    <div className="upload-container">
      <div className="page-header">
        <h1 className="page-title">📤 Bulk Upload</h1>
        <p className="page-subtitle">
          Upload documents to the knowledge base. All files are parsed, classified by AI, and indexed for semantic search.
        </p>
      </div>

      {files.length > 0 && (
        <div className="stats-row" style={{ marginBottom: '20px' }}>
          <div className="stat-chip"><span>📁</span><span><strong>{files.length}</strong> total</span></div>
          {processingCount > 0 && <div className="stat-chip"><span>⚙️</span><span><strong>{processingCount}</strong> processing</span></div>}
          {indexedCount > 0 && <div className="stat-chip"><span>✅</span><span><strong>{indexedCount}</strong> indexed</span></div>}
        </div>
      )}

      <div
        className={`drop-zone ${dragging ? 'drag-over' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <span className="drop-zone-icon">{dragging ? '🎯' : '☁️'}</span>
        <div className="drop-zone-title">{dragging ? 'Drop your files here' : 'Drag & drop files here'}</div>
        <div className="drop-zone-sub">or click to browse files</div>
        <div className="drop-zone-types">
          <span className="type-badge">📕 PDF</span>
          <span className="type-badge">🖼️ PNG / JPG</span>
          <span className="type-badge">📄 TXT</span>
          <span className="type-badge">📦 Multiple files</span>
          <span className="type-badge">50MB max each</span>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.txt"
          onChange={handleFileInput}
          style={{ display: 'none' }}
          id="file-input"
        />
      </div>

      {files.length > 0 && (
        <div style={{ display: 'flex', gap: '10px', marginTop: '16px', flexWrap: 'wrap' }}>
          {pendingCount > 0 && (
            <button className="btn btn-primary" onClick={uploadAll} disabled={uploading}>
              {uploading
                ? <><div className="spinner" style={{ borderTopColor: 'white', width: '16px', height: '16px' }}></div> Uploading…</>
                : `⬆️ Upload ${pendingCount} file${pendingCount !== 1 ? 's' : ''}`}
            </button>
          )}
          {(indexedCount > 0 || files.some(f => f.status === 'error')) && (
            <button className="btn btn-ghost" onClick={clearCompleted}>🧹 Clear completed</button>
          )}
          <button className="btn btn-ghost" onClick={() => fileInputRef.current?.click()}>➕ Add more files</button>
        </div>
      )}

      <div style={{
        marginTop: '12px', padding: '10px 14px',
        background: 'rgba(99, 102, 241, 0.05)',
        border: '1px solid rgba(99, 102, 241, 0.1)',
        borderRadius: 'var(--radius-sm)',
        fontSize: '12px', color: 'var(--text-muted)',
        display: 'flex', alignItems: 'center', gap: '8px',
      }}>
        🔒 <span>Files are validated by MIME type, renamed to UUIDs, and stored securely outside the web root. API key required.</span>
      </div>

      {files.length > 0 && (
        <div className="file-list">
          {files.map((f, i) => (
            <div key={i} className={`file-card status-${f.status}`}>
              <div className="file-card-header">
                <div className={`file-icon ${getFileClass(f.file.name)}`}>{getFileIcon(f.file.name)}</div>
                <div className="file-info">
                  <div className="file-name">{f.file.name}</div>
                  <div className="file-meta">{formatBytes(f.file.size)}</div>
                </div>
                <div className={`status-badge ${f.status}`}>
                  {f.status === 'parsing' && '⚙️ '}
                  {f.status === 'classifying' && '🧠 '}
                  {f.status === 'indexing' && '📊 '}
                  {f.status === 'indexed' && '✅ '}
                  {f.status === 'error' && '❌ '}
                  {f.status === 'pending' && '⏳ '}
                  {f.status}
                </div>
              </div>

              {f.progress > 0 && f.progress < 100 && (
                <div className="progress-bar-wrapper">
                  <div className="progress-bar" style={{ width: `${f.progress}%` }}></div>
                </div>
              )}

              <div className="status-message">{f.message}</div>

              {f.error && (
                <div style={{
                  marginTop: '8px', padding: '8px 12px',
                  background: 'rgba(239, 68, 68, 0.05)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px', color: 'var(--accent-danger)',
                }}>
                  {f.error}
                </div>
              )}

              {f.classification && (
                <div className="classification-card">
                  <div className="classification-title">AI Classification Results</div>
                  <div style={{ marginBottom: '10px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {f.classification.summary}
                  </div>
                  <div className="classification-grid">
                    <div className="class-item">
                      <div className="class-label">Type</div>
                      <div className="class-value" style={{ textTransform: 'capitalize' }}>{f.classification.document_type}</div>
                    </div>
                    <div className="class-item">
                      <div className="class-label">Topic</div>
                      <div className="class-value">{f.classification.topic}</div>
                    </div>
                    <div className="class-item">
                      <div className="class-label">Language</div>
                      <div className="class-value">{f.classification.language}</div>
                    </div>
                    <div className="class-item">
                      <div className="class-label">Sensitivity</div>
                      <div>
                        <span
                          className={`sensitivity-badge ${f.classification.sensitivity_level}`}
                          style={{ color: sensitivityColors[f.classification.sensitivity_level] }}
                        >
                          {f.classification.sensitivity_level.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                    <div className="class-item">
                      <div className="class-label">Features</div>
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {f.classification.has_tables && <span className="tag">Tables</span>}
                        {f.classification.has_images && <span className="tag">Images</span>}
                        {f.classification.has_handwriting && <span className="tag">Handwriting</span>}
                      </div>
                    </div>
                  </div>
                  {f.classification.key_entities.length > 0 && (
                    <div style={{ marginTop: '10px' }}>
                      <div className="class-label" style={{ marginBottom: '4px' }}>Key Entities</div>
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {f.classification.key_entities.slice(0, 8).map((e, j) => (
                          <span key={j} className="tag">{e}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {files.length === 0 && (
        <div style={{ marginTop: '32px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>📂</div>
          No files selected yet. Drag & drop or click the area above.
        </div>
      )}
    </div>
  )
}
