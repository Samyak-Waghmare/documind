'use client'

import { useEffect, useState } from 'react'
import { DocumentRecord } from '@/lib/types'
import { API_BASE } from '@/lib/api'
import Link from 'next/link'

const sensitivityColors: Record<string, string> = {
  public: 'var(--accent-success)',
  internal: 'var(--accent-warning)',
  confidential: '#f97316',
  strictly_confidential: 'var(--accent-danger)',
}

const docTypeIcons: Record<string, string> = {
  financial: '💰', report: '📊', invoice: '🧾',
  academic: '🎓', medical: '🏥', legal: '⚖️',
  technical: '⚙️', news: '📰', contract: '📋',
  letter: '✉️', handwritten: '✍️', other: '📄',
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    fetch(`${API_BASE}/documents`)
      .then(r => r.json())
      .then(data => {
        setDocs(Array.isArray(data) ? data : [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const filtered = filter === 'all' ? docs : docs.filter(d => d.status === filter)

  return (
    <div className="upload-container">
      <div className="page-header">
        <h1 className="page-title">📚 Knowledge Base</h1>
        <p className="page-subtitle">
          All indexed documents available for AI-powered semantic search and Q&A.
        </p>
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
        {['all', 'indexed', 'parsing', 'error'].map(s => (
          <button
            key={s}
            className={`btn ${filter === s ? 'btn-primary btn-sm' : 'btn-ghost btn-sm'}`}
            onClick={() => setFilter(s)}
          >
            {s === 'all' ? `All (${docs.length})` : `${s} (${docs.filter(d => d.status === s).length})`}
          </button>
        ))}
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => {
            setLoading(true)
            fetch(`${API_BASE}/documents`).then(r => r.json()).then(d => { setDocs(d); setLoading(false) })
          }}
        >
          🔄 Refresh
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          <div className="spinner" style={{ margin: '0 auto 16px', width: '32px', height: '32px' }}></div>
          Loading documents…
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📂</div>
          <div className="empty-state-title">No documents found</div>
          <div className="empty-state-sub">
            {docs.length === 0
              ? 'Upload documents to build your knowledge base.'
              : 'No documents match the current filter.'}
          </div>
          <Link href="/upload" className="btn btn-primary">
            📤 Upload Documents
          </Link>
        </div>
      ) : (
        <div className="file-list">
          {filtered.map(doc => (
            <div key={doc.doc_id} className={`file-card status-${doc.status}`}>
              <div className="file-card-header">
                <div className="file-icon pdf" style={{ fontSize: '20px', background: 'rgba(99,102,241,0.1)' }}>
                  {doc.classification ? (docTypeIcons[doc.classification.document_type] || '📄') : '📄'}
                </div>
                <div className="file-info">
                  <div className="file-name">{doc.original_filename}</div>
                  <div className="file-meta">
                    {doc.num_pages > 0 && `${doc.num_pages} pages · `}
                    {new Date(doc.upload_time).toLocaleDateString()}
                  </div>
                </div>
                <div className={`status-badge ${doc.status}`}>{doc.status}</div>
              </div>

              {doc.classification && (
                <div className="classification-card">
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center', marginBottom: '8px' }}>
                    <span className="tag" style={{ textTransform: 'capitalize' }}>
                      {doc.classification.document_type}
                    </span>
                    <span className={`sensitivity-badge ${doc.classification.sensitivity_level}`}
                      style={{ color: sensitivityColors[doc.classification.sensitivity_level] }}>
                      🔒 {doc.classification.sensitivity_level.replace('_', ' ')}
                    </span>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {doc.classification.language}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                    {doc.classification.summary}
                  </div>
                  {doc.classification.key_entities.length > 0 && (
                    <div style={{ marginTop: '8px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                      {doc.classification.key_entities.slice(0, 6).map((e, i) => (
                        <span key={i} className="tag">{e}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {doc.error_message && (
                <div style={{
                  marginTop: '8px', padding: '8px', fontSize: '12px',
                  color: 'var(--accent-danger)',
                  background: 'rgba(239,68,68,0.05)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid rgba(239,68,68,0.2)',
                }}>
                  {doc.error_message}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
