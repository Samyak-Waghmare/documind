import type { Metadata } from 'next'
import ChatInterface from '@/components/ChatInterface'

export const metadata: Metadata = {
  title: 'DocuMind — AI Chatbot with Document Citations',
  description: 'Ask questions about your documents and get grounded answers with exact source citations and page images.',
}

export default function Home() {
  return <ChatInterface />
}
