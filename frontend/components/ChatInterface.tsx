'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Citation, ChatMessage } from '@/lib/types'
import { apiFetch, API_BASE } from '@/lib/api'
import PageModal from './PageModal'

interface VoiceState {
  listening: boolean
  transcript: string
  supported: boolean
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null)
  const [voice, setVoice] = useState<VoiceState>({ listening: false, transcript: '', supported: false })
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const recognitionRef = useRef<any>(null)

  useEffect(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (SR) setVoice(v => ({ ...v, supported: true }))
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px'
    }
  }, [input])

  const sendMessage = useCallback(async (text?: string) => {
    const messageText = (text || input).trim()
    if (!messageText || loading) return

    const userMsg: ChatMessage = { role: 'user', content: messageText }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await apiFetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText, history: messages.slice(-10), session_id: sessionId }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const data = await res.json()
      setSessionId(data.session_id)
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer, citations: data.citations }])
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ Error: ${err.message}`,
        citations: [],
      }])
    } finally {
      setLoading(false)
      setTimeout(() => textareaRef.current?.focus(), 100)
    }
  }, [input, loading, messages, sessionId])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const toggleVoice = useCallback(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) return

    if (voice.listening) {
      recognitionRef.current?.stop()
      setVoice(v => ({ ...v, listening: false }))
      return
    }

    const recognition = new SR()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (e: any) => {
      let final = '', interim = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) final += e.results[i][0].transcript
        else interim += e.results[i][0].transcript
      }
      if (final) setInput(prev => prev + final)
      setVoice(v => ({ ...v, transcript: interim }))
    }

    recognition.onend = () => setVoice(v => ({ ...v, listening: false, transcript: '' }))
    recognition.onerror = () => setVoice(v => ({ ...v, listening: false, transcript: '' }))

    recognitionRef.current = recognition
    recognition.start()
    setVoice(v => ({ ...v, listening: true, transcript: '' }))
  }, [voice.listening])

  const suggestions = [
    "What are the key financial metrics in the annual report?",
    "Summarize the medical report findings",
    "What are the main clauses in the software license agreement?",
    "What revenue did ACME Corporation report?",
    "What is the sensitivity level of the medical document?",
  ]

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '36px', height: '36px',
            background: 'linear-gradient(135deg, #06b6d4, #6366f1)',
            borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '18px',
          }}>🤖</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '15px' }}>AI Document Assistant</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Powered by Gemini · Grounded citations · No hallucination
            </div>
          </div>
        </div>
        <div className="stats-row">
          <div className="stat-chip">
            <span>💬</span>
            <span><strong>{messages.filter(m => m.role === 'user').length}</strong> messages</span>
          </div>
          {sessionId && (
            <div className="stat-chip">
              <span>🔗</span>
              <span>Session active</span>
            </div>
          )}
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state" style={{ justifyContent: 'flex-start', paddingTop: '40px' }}>
            <div className="welcome-card">
              <h2>Welcome to DocuMind AI</h2>
              <p>
                Ask questions about your uploaded documents. Every answer comes with
                exact source citations — document name + page number + thumbnail preview.
              </p>
              <div className="suggestion-chips">
                {suggestions.map((s, i) => (
                  <button key={i} className="suggestion-chip" onClick={() => sendMessage(s)} disabled={loading}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message-wrapper ${msg.role}`}>
            <div className={`message-avatar ${msg.role}`}>
              {msg.role === 'user' ? '👤' : '🤖'}
            </div>
            <div className="message-content">
              <div className={`message-bubble ${msg.role}`}>
                {msg.content.split('\n').map((line, j) => (
                  <p key={j} style={{ margin: line ? undefined : '0' }}>{line || '\u00A0'}</p>
                ))}
              </div>

              {msg.citations && msg.citations.length > 0 && (
                <div className="citations-section">
                  <div className="citations-label">
                    <span>📎</span>
                    Sources ({msg.citations.length})
                  </div>
                  <div className="citations-grid">
                    {msg.citations.map((cite, j) => (
                      <button
                        key={j}
                        className="citation-chip"
                        onClick={() => setSelectedCitation(cite)}
                        title={`${cite.doc_name}, Page ${cite.page_num}`}
                      >
                        {cite.image_path && (
                          <div className="citation-thumbnail">
                            <img
                              src={`${API_BASE}/uploads/${cite.image_path}`}
                              alt={`Page ${cite.page_num}`}
                              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                            />
                          </div>
                        )}
                        <div className="citation-info">
                          <div className="citation-doc" title={cite.doc_name}>{cite.doc_name}</div>
                          <div className="citation-page">Page {cite.page_num}</div>
                        </div>
                        <div className="citation-score">{(cite.score * 100).toFixed(0)}%</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message-wrapper assistant">
            <div className="message-avatar assistant">🤖</div>
            <div className="message-content">
              <div className="message-bubble assistant">
                <div className="thinking-dots">
                  <div className="thinking-dot"></div>
                  <div className="thinking-dot"></div>
                  <div className="thinking-dot"></div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        {voice.listening && (
          <div className="voice-transcript">
            <div className="voice-indicator"></div>
            <span>{voice.transcript || 'Listening… speak now'}</span>
          </div>
        )}
        <div className="chat-input-row">
          {voice.supported && (
            <button
              className={`btn btn-voice ${voice.listening ? 'listening' : ''}`}
              onClick={toggleVoice}
              title={voice.listening ? 'Stop recording' : 'Voice input'}
            >
              {voice.listening ? '⏹' : '🎤'}
            </button>
          )}
          <textarea
            ref={textareaRef}
            className="chat-input-box"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your documents… (Enter to send, Shift+Enter for newline)"
            rows={1}
            disabled={loading}
          />
          <button
            className="chat-send-btn"
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            title="Send message"
          >
            {loading
              ? <div className="spinner" style={{ borderTopColor: 'white', width: '18px', height: '18px' }}></div>
              : '➤'}
          </button>
        </div>
      </div>

      {selectedCitation && (
        <PageModal citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
      )}
    </div>
  )
}
