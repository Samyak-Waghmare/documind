'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { API_BASE } from '@/lib/api'

export default function Sidebar() {
  const pathname = usePathname()
  const [docCount, setDocCount] = useState(0)

  useEffect(() => {
    fetch(`${API_BASE}/documents`)
      .then(r => r.json())
      .then(docs => setDocCount(Array.isArray(docs) ? docs.length : 0))
      .catch(() => {})
  }, [])

  return (
    <nav className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">🧠</div>
        <div>
          <div className="sidebar-logo-text">DocuMind</div>
          <div className="sidebar-logo-sub">Document Intelligence</div>
        </div>
      </div>

      {/* Navigation */}
      <span className="nav-section-label">Navigation</span>

      <Link
        href="/"
        className={`nav-link ${pathname === '/' ? 'active' : ''}`}
      >
        <span className="nav-link-icon">💬</span>
        AI Chatbot
      </Link>

      <Link
        href="/upload"
        className={`nav-link ${pathname === '/upload' ? 'active' : ''}`}
      >
        <span className="nav-link-icon">📤</span>
        Bulk Upload
      </Link>

      <Link
        href="/documents"
        className={`nav-link ${pathname === '/documents' ? 'active' : ''}`}
      >
        <span className="nav-link-icon">📚</span>
        Knowledge Base
        {docCount > 0 && (
          <span style={{
            marginLeft: 'auto',
            background: 'rgba(99,102,241,0.2)',
            borderRadius: '10px',
            padding: '1px 8px',
            fontSize: '11px',
            color: 'var(--accent-primary)',
          }}>
            {docCount}
          </span>
        )}
      </Link>

      {/* Info */}
      <div style={{ marginTop: 'auto', padding: '12px', borderTop: '1px solid var(--border-secondary)' }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.6' }}>
          <div style={{ marginBottom: '4px', fontWeight: 600, color: 'var(--text-secondary)' }}>🔒 Security</div>
          <div>API key protected</div>
          <div>MIME validation</div>
          <div>UUID file storage</div>
        </div>
      </div>
    </nav>
  )
}
