'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Feedback {
  id: string
  text: string
  source: string
  source_id: string
  account?: string
  created_at: string
  confidence: number
  doc_url?: string
  speaker?: string
  started_at?: string
  ended_at?: string
  meta?: any
}

interface InsightDetail {
  id: string
  title: string
  description?: string
  impact?: string
  recommendation?: string
  severity: string
  effort: string
  priority_score: number
  feedback_count: number
  metrics?: {
    score: number
    freq_30d: number
    freq_90d: number
    acv_sum: number
    sentiment: number
    trend: number
    dup_penalty: number
  }
  key_quotes: Feedback[]
  supporting_feedback: Feedback[]
}

const SOURCE_ICONS: Record<string, string> = {
  slack: '💬',
  jira: '🎫',
  gdoc: '📄',
  zoom: '🎥',
}

const SOURCE_COLORS: Record<string, string> = {
  slack: 'bg-purple-100 text-purple-800',
  jira: 'bg-blue-100 text-blue-800',
  gdoc: 'bg-green-100 text-green-800',
  zoom: 'bg-orange-100 text-orange-800',
}

const SEVERITY_COLORS: Record<string, string> = {
  low: 'bg-gray-100 text-gray-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
}

const EFFORT_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
}

export default function InsightDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [insight, setInsight] = useState<InsightDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedSupporting, setExpandedSupporting] = useState(false)

  useEffect(() => {
    if (params.id) {
      fetchInsight(params.id as string)
    }
  }, [params.id])

  const fetchInsight = async (id: string) => {
    try {
      const response = await fetch(`${API_URL}/themes/${id}`)
      if (!response.ok) throw new Error('Insight not found')
      const data = await response.json()
      setInsight(data)
    } catch (error) {
      console.error('Failed to fetch insight:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleSupporting = () => {
    setExpandedSupporting((prev) => !prev)
  }

  const renderFeedback = (feedback: Feedback, isKeyQuote: boolean = false) => {
    const sourceIcon = SOURCE_ICONS[feedback.source] || '📌'
    const sourceColor = SOURCE_COLORS[feedback.source] || 'bg-gray-100 text-gray-800'

    // Format time range for Zoom
    let timeRange = ''
    if (feedback.source === 'zoom' && feedback.started_at && feedback.ended_at) {
      const start = new Date(feedback.started_at)
      const end = new Date(feedback.ended_at)
      const startMin = start.getMinutes()
      const startSec = start.getSeconds()
      const endMin = end.getMinutes()
      const endSec = end.getSeconds()
      timeRange = `${startMin}:${startSec.toString().padStart(2, '0')}–${endMin}:${endSec.toString().padStart(2, '0')}`
    }

    return (
      <div
        key={feedback.id}
        className={`border-l-4 ${isKeyQuote ? 'border-blue-500 bg-blue-50' : 'border-gray-300'} pl-4 py-3 ${isKeyQuote ? '' : 'opacity-75'}`}
      >
        <p className="text-gray-800 mb-3">&quot;{feedback.text}&quot;</p>

        <div className="flex flex-wrap gap-2 items-center">
          {/* Source chip */}
          <span className={`px-2 py-1 rounded text-xs font-medium ${sourceColor}`}>
            {sourceIcon} {feedback.source.toUpperCase()}
          </span>

          {/* Account */}
          {feedback.account && (
            <span className="text-sm text-gray-600 font-medium">
              {feedback.account}
            </span>
          )}

          {/* Date */}
          <span className="text-sm text-gray-500">
            {new Date(feedback.created_at).toLocaleDateString()}
          </span>

          {/* Speaker (Zoom) */}
          {feedback.speaker && (
            <span className="text-sm text-gray-600">
              🎤 {feedback.speaker}
            </span>
          )}

          {/* Time range (Zoom) */}
          {timeRange && (
            <span className="text-sm text-gray-600">⏱️ {timeRange}</span>
          )}

          {/* Confidence */}
          <span className="text-sm text-blue-600">
            {(feedback.confidence * 100).toFixed(0)}% confidence
          </span>

          {/* Citation link */}
          {feedback.doc_url && !feedback.doc_url.startsWith('file://') && (
            <a
              href={feedback.doc_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline flex items-center gap-1"
            >
              View source ↗
            </a>
          )}
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading insight...</div>
      </div>
    )
  }

  if (!insight) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-lg mb-4">Insight not found</p>
          <Link href="/" className="text-blue-600 hover:underline">
            Back to insights
          </Link>
        </div>
      </div>
    )
  }

  const severityColor = SEVERITY_COLORS[insight.severity] || SEVERITY_COLORS.medium
  const effortColor = EFFORT_COLORS[insight.effort] || EFFORT_COLORS.medium

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link href="/" className="text-blue-600 hover:underline">
            ← Back to insights
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-start justify-between mb-4">
          <h1 className="text-3xl font-bold flex-1">{insight.title}</h1>
          <div className="flex gap-2 ml-4">
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${severityColor}`}>
              {insight.severity.toUpperCase()}
            </span>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${effortColor}`}>
              {insight.effort.toUpperCase()} EFFORT
            </span>
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              P{insight.priority_score}
            </span>
          </div>
        </div>

        {insight.description && (
          <p className="text-gray-700 mb-6">{insight.description}</p>
        )}

        {/* Impact & Recommendation */}
        <div className="grid md:grid-cols-2 gap-4 mb-8">
          {insight.impact && (
            <div className="bg-orange-50 p-4 rounded border-l-4 border-orange-500">
              <div className="text-sm font-semibold text-orange-800 mb-1">💥 Impact</div>
              <p className="text-sm text-gray-700">{insight.impact}</p>
            </div>
          )}
          {insight.recommendation && (
            <div className="bg-green-50 p-4 rounded border-l-4 border-green-500">
              <div className="text-sm font-semibold text-green-800 mb-1">✅ Recommendation</div>
              <p className="text-sm text-gray-700">{insight.recommendation}</p>
            </div>
          )}
        </div>

        {/* Metrics */}
        {insight.metrics && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Score Breakdown</h2>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="text-center p-4 bg-blue-50 rounded">
                <div className="text-3xl font-bold text-blue-600">
                  {insight.metrics.score.toFixed(2)}
                </div>
                <div className="text-sm text-gray-600">Overall Score</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded">
                <div className="text-2xl font-bold text-green-600">
                  {insight.metrics.freq_30d}
                </div>
                <div className="text-sm text-gray-600">30d Frequency</div>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded">
                <div className="text-2xl font-bold text-purple-600">
                  ${(insight.metrics.acv_sum / 1000).toFixed(0)}k
                </div>
                <div className="text-sm text-gray-600">Total ACV</div>
              </div>
              <div className="text-center p-4 bg-orange-50 rounded">
                <div className="text-2xl font-bold text-orange-600">
                  {insight.metrics.trend > 0 ? '↗' : '→'}
                </div>
                <div className="text-sm text-gray-600">Trend</div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">90d Frequency:</span>
                <span className="ml-2 font-medium">{insight.metrics.freq_90d}</span>
              </div>
              <div>
                <span className="text-gray-600">Sentiment:</span>
                <span className="ml-2 font-medium">{insight.metrics.sentiment.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-gray-600">Trend Momentum:</span>
                <span className="ml-2 font-medium">{insight.metrics.trend.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-gray-600">Dup Penalty:</span>
                <span className="ml-2 font-medium">{insight.metrics.dup_penalty.toFixed(2)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Evidence Section */}
        <div className="space-y-6">
          {/* Key Quotes */}
          {insight.key_quotes.length > 0 && (
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="p-6 bg-gray-50">
                <h4 className="font-semibold mb-4 text-sm uppercase tracking-wide text-gray-700">
                  🎯 Key Evidence ({insight.key_quotes.length})
                </h4>
                <div className="space-y-3">
                  {insight.key_quotes.map((feedback) => renderFeedback(feedback, true))}
                </div>
              </div>
            </div>
          )}

          {/* Supporting Feedback (Collapsible) */}
          {insight.supporting_feedback.length > 0 && (
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="p-6">
                <button
                  onClick={toggleSupporting}
                  className="w-full flex items-center justify-between text-left font-semibold text-sm uppercase tracking-wide text-gray-700 hover:text-gray-900"
                >
                  <span>
                    📋 Supporting Feedback ({insight.supporting_feedback.length})
                  </span>
                  <span className="text-lg">{expandedSupporting ? '▼' : '▶'}</span>
                </button>

                {expandedSupporting && (
                  <div className="mt-4 space-y-3">
                    {insight.supporting_feedback.map((feedback) => renderFeedback(feedback, false))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
