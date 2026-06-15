import type { Metadata } from 'next'
import UploadPage from '@/components/UploadPage'

export const metadata: Metadata = {
  title: 'DocuMind — Bulk Document Upload',
  description: 'Upload multiple documents at once. Get real-time parsing, AI classification, and vector indexing status.',
}

export default function Upload() {
  return <UploadPage />
}
