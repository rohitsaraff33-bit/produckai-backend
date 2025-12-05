'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Layout from '../../../components/Layout'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface FeedbackItem {
  id: string
  source: string
  source_id: string
  text: string
  account: string
  created_at: string
  meta?: {
    title?: string
    url?: string
    modified_time?: string
    owner?: string
  }
}

interface DocumentSummary {
  document_id: string
  title: string
  url?: string
  account?: string
  created_at: string
  modified_at?: string
  chunk_count: number
  summary: string
  owner?: string
}

const SOURCE_INFO: Record<string, { name: string; icon: string; color: string }> = {
  slack: { name: 'Slack', icon: '💬', color: 'purple' },
  jira: { name: 'Jira', icon: '🎫', color: 'blue' },
  zoom: { name: 'Zoom', icon: '🎥', color: 'blue' },
  gdrive: { name: 'Google Drive', icon: '📄', color: 'green' },
}

export default function SourceDetailPage() {
  const params = useParams()
  const router = useRouter()
  const source = params.source as string

  const [feedbackItems, setFeedbackItems] = useState<FeedbackItem[]>([])
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const sourceInfo = SOURCE_INFO[source] || { name: source, icon: '📁', color: 'gray' }

  // Sources that use chunking and should show document view
  const usesDocumentView = ['gdrive', 'zoom'].includes(source)

  useEffect(() => {
    fetchSourceData()
  }, [source])

  const fetchSourceData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Map source ID to API source enum
      const sourceMap: Record<string, string> = {
        'slack': 'slack',
        'jira': 'jira',
        'zoom': 'zoom_transcript',
        'gdrive': 'gdoc',
      }

      const apiSource = sourceMap[source] || source

      // Use document view for sources that chunk transcripts
      if (usesDocumentView) {
        const response = await fetch(`${API_URL}/feedback/documents?source=${apiSource}`)
        if (!response.ok) {
          throw new Error('Failed to fetch documents')
        }
        const data = await response.json()
        setDocuments(data)
      } else {
        const response = await fetch(`${API_URL}/feedback?source=${apiSource}`)
        if (!response.ok) {
          throw new Error('Failed to fetch feedback items')
        }
        const data = await response.json()
        setFeedbackItems(data)
      }
    } catch (err) {
      console.error('Error fetching source data:', err)
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <div className="text-4xl mb-4">{sourceInfo.icon}</div>
            <div className="text-lg">Loading {sourceInfo.name} data...</div>
          </div>
        </div>
      </Layout>
    )
  }

  if (error) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <div className="text-4xl mb-4">⚠️</div>
            <div className="text-lg text-red-400">Error: {error}</div>
            <button
              onClick={() => router.back()}
              className="mt-4 px-4 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] rounded"
            >
              Go Back
            </button>
          </div>
        </div>
      </Layout>
    )
  }

  const itemCount = usesDocumentView ? documents.length : feedbackItems.length
  const hasItems = itemCount > 0

  // Get unique account for summary (for Google Drive, get owner email)
  const accountSummary = usesDocumentView && documents.length > 0
    ? documents[0].owner || 'Multiple accounts'
    : null

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.back()}
            className="mb-4 text-sm text-gray-400 hover:text-gray-200 flex items-center gap-2"
          >
            ← Back
          </button>
          <div className="flex items-center gap-4">
            <div className="text-4xl">{sourceInfo.icon}</div>
            <h1 className="text-3xl font-bold text-gray-100">{sourceInfo.name}</h1>
          </div>
        </div>

        {/* Summary Section for Document View */}
        {usesDocumentView && hasItems && (
          <div className="bg-[#252526] border border-[#3e3e42] rounded-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-100 mb-3">
              Summary of {sourceInfo.name} ingested for insight analysis
            </h2>
            <div className="flex flex-wrap gap-4 text-sm text-gray-300">
              {accountSummary && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">Account:</span>
                  <span className="font-medium">{accountSummary}</span>
                </div>
              )}
              <div className="flex items-center gap-2">
                <span className="text-gray-400">Total Documents:</span>
                <span className="font-medium">{itemCount}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">Total Statements:</span>
                <span className="font-medium">
                  {documents.reduce((sum, doc) => sum + doc.chunk_count, 0)}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Content */}
        {!hasItems ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">{sourceInfo.icon}</div>
            <div className="text-xl text-gray-400 mb-2">No items found</div>
            <p className="text-sm text-gray-500">
              {usesDocumentView ? 'Documents' : 'Feedback items'} from {sourceInfo.name} will appear here once synced
            </p>
          </div>
        ) : usesDocumentView ? (
          // Document View (for chunked sources like Google Drive, Zoom)
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {documents.map((doc) => (
              <div
                key={doc.document_id}
                className="bg-[#252526] border border-[#3e3e42] rounded-lg p-5 hover:border-[#4e4e52] transition-all hover:shadow-lg"
              >
                <div className="flex flex-col h-full">
                  {/* Title */}
                  <h3 className="text-lg font-semibold text-gray-100 mb-3 line-clamp-2">
                    {doc.title}
                  </h3>

                  {/* Metadata Badges */}
                  <div className="flex items-center gap-2 mb-4 flex-wrap">
                    {doc.account && (
                      <span className="inline-flex items-center gap-1 bg-blue-500/20 text-blue-300 px-2 py-1 rounded text-xs font-medium">
                        📊 {doc.account}
                      </span>
                    )}
                    <span className="inline-flex items-center gap-1 bg-[#3e3e42] text-gray-300 px-2 py-1 rounded text-xs font-medium">
                      💬 {doc.chunk_count} statements
                    </span>
                  </div>

                  {/* Date */}
                  <div className="text-xs text-gray-400 mb-4">
                    {formatDate(doc.created_at)}
                  </div>

                  {/* View Source Button */}
                  {doc.url && (
                    <a
                      href={doc.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-auto w-full px-4 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] rounded text-sm font-medium transition-colors text-center"
                    >
                      View Source →
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          // Feedback Items View (for non-chunked sources like Slack, Jira)
          <div className="space-y-4">
            {feedbackItems.map((item) => (
              <div
                key={item.id}
                className="bg-[#252526] border border-[#3e3e42] rounded-lg p-5 hover:border-[#4e4e52] transition-colors"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-100 mb-1">
                      {item.meta?.title || `${sourceInfo.name} Item`}
                    </h3>
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                      <span>ID: {item.source_id}</span>
                      {item.account && <span>Account: {item.account}</span>}
                      <span>{formatDate(item.created_at)}</span>
                    </div>
                  </div>
                  {item.meta?.url && (
                    <a
                      href={item.meta.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-4 px-3 py-1.5 bg-[#3e3e42] hover:bg-[#4e4e52] rounded text-xs font-medium transition-colors flex items-center gap-1.5"
                    >
                      View Source →
                    </a>
                  )}
                </div>

                {/* Metadata */}
                {(item.meta?.owner || item.meta?.modified_time) && (
                  <div className="flex gap-4 mb-3 text-xs">
                    {item.meta?.owner && (
                      <div className="flex items-center gap-1.5 text-gray-400">
                        <span>👤</span>
                        <span>{item.meta.owner}</span>
                      </div>
                    )}
                    {item.meta?.modified_time && (
                      <div className="flex items-center gap-1.5 text-gray-400">
                        <span>🕒</span>
                        <span>Modified {formatDate(item.meta.modified_time)}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Content Preview */}
                <div className="mt-3 p-3 bg-[#1e1e1e] rounded border border-[#3e3e42]">
                  <p className="text-sm text-gray-300 line-clamp-4 whitespace-pre-wrap">
                    {item.text}
                  </p>
                  {item.text.length > 400 && (
                    <button className="mt-2 text-xs text-blue-400 hover:text-blue-300">
                      Show more →
                    </button>
                  )}
                </div>

                {/* Footer Stats */}
                <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
                  <span>{item.text.length} characters</span>
                  <span>•</span>
                  <span>{Math.ceil(item.text.split(/\s+/).length / 200)} min read</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}
