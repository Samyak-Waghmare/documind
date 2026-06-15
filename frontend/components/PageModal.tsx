'use client'

import { Citation } from '@/lib/types'
import { API_BASE } from '@/lib/api'
import { useEffect, useRef } from 'react'

interface PageModalProps {
  citation: Citation
  onClose: () => void
}

export default function PageModal({ citation, onClose }: PageModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) onClose()
  }

  const sensitivityColor = (text: string) => {
    if (text.includes('confidential')) return 'var(--accent-danger)'
    if (text.includes('internal')) return 'var(--accent-warning)'
    return 'var(--accent-success)'
  }

  return (
    <div className="modal-overlay" ref={overlayRef} onClick={handleOverlayClick}>
      <div className="modal">
        <div className="modal-header">
          <div className="modal-title">
            📄 {citation.doc_name} — Page {citation.page_num}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              background: 'rgba(16, 185, 129, 0.1)',
              color: 'var(--accent-success)',
              borderRadius: '12px',
              padding: '2px 10px',
              fontSize: '11px',
              fontWeight: 700,
            }}>
              {(citation.score * 100).toFixed(1)}% match
            </div>
            <button
              className="btn btn-ghost btn-sm btn-icon"
              onClick={onClose}
              style={{ fontSize: '18px' }}
            >
              ×
            </button>
          </div>
        </div>

        <div className="modal-body">
          {/* Document info */}
          <div style={{
            display: 'flex', gap: '12px', marginBottom: '16px',
            flexWrap: 'wrap',
          }}>
            <div className="stat-chip">
              <span>📄</span>
              <span>{citation.doc_name}</span>
            </div>
            <div className="stat-chip">
              <span>📖</span>
              <span>Page <strong>{citation.page_num}</strong></span>
            </div>
          </div>

          {/* Page image */}
          {citation.image_path ? (
            <div style={{ textAlign: 'center', marginBottom: '16px' }}>
              <img
                src={`${API_BASE}/uploads/${citation.image_path}`}
                alt={`Page ${citation.page_num} of ${citation.doc_name}`}
                className="page-image-full"
                onError={(e) => {
                  const div = document.createElement('div')
                  div.style.cssText = `
                    padding: 40px; text-align: center; 
                    background: var(--bg-secondary); 
                    border-radius: var(--radius-sm);
                    border: 1px dashed var(--border-secondary);
                    color: var(--text-muted); font-size: 14px;
                  `
                  div.textContent = '🖼️ Page image not available (install Poppler for PDF rendering)'
                  ;(e.target as HTMLImageElement).replaceWith(div)
                }}
              />
            </div>
          ) : (
            <div style={{
              padding: '40px', textAlign: 'center',
              background: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-sm)',
              border: '1px dashed var(--border-secondary)',
              marginBottom: '16px',
              color: 'var(--text-muted)',
            }}>
              🖼️ Page image not available
            </div>
          )}

          {/* Matched chunk text */}
          <div style={{ marginBottom: '8px', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            📝 Matched Text Chunk
          </div>
          <div className="chunk-text-preview">
            {citation.chunk_text}
          </div>
        </div>
      </div>
    </div>
  )
}
