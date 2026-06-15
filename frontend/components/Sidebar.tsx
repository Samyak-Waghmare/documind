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
        <div className="sidebar-logo-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
        </div>
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
