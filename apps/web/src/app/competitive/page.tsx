'use client'

import { useState, useEffect } from 'react'
import Layout from '@/components/Layout'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface CompetitiveInsight {
  id: string
  title: string
  description?: string
  impact?: string
  recommendation?: string
  severity: string
  effort: string
  priority_score: number
  created_at: string
  competitor_name: string
  competitor_moves?: Array<{
    move: string
    date: string
    source_url: string
  }>
  evidence_count?: string
  mentions_30d?: string
  impacted_acv_usd?: string
  est_method?: string
  citations?: Array<{
    title: string
    url: string
    snippet: string
  }>
}

interface ResearchSession {
  id: string
  company_name: string
  market_scope: string
  target_personas: string[]
  geo_segments: string[]
  competitors_researched: string[]
  insights_generated?: string[]
  status: string
  error_message?: string
  started_at: string
  completed_at?: string
}

interface CompetitorMove {
  move: string
  date: string
  source_url: string
}

interface CompetitorInput {
  name: string
  description: string
  moves: CompetitorMove[]
}

const SEVERITY_COLORS: Record<string, string> = {
  low: 'bg-gray-700 text-gray-300',
  medium: 'bg-yellow-600 text-yellow-100',
  high: 'bg-orange-600 text-orange-100',
  critical: 'bg-red-600 text-red-100',
}

const EFFORT_COLORS: Record<string, string> = {
  low: 'bg-green-700 text-green-100',
  medium: 'bg-yellow-600 text-yellow-100',
  high: 'bg-red-700 text-red-100',
}

export default function CompetitivePage() {
  const [insights, setInsights] = useState<CompetitiveInsight[]>([])
  const [sessions, setSessions] = useState<ResearchSession[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedInsight, setExpandedInsight] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  // Form state
  const [mode, setMode] = useState<'auto' | 'manual'>('auto')
  const [companyName, setCompanyName] = useState('')
  const [marketScope, setMarketScope] = useState('')
  const [competitorNames, setCompetitorNames] = useState('') // For auto mode
  const [targetPersonas, setTargetPersonas] = useState<string[]>([''])
  const [geoSegments, setGeoSegments] = useState<string[]>([''])
  const [competitors, setCompetitors] = useState<CompetitorInput[]>([{
    name: '',
    description: '',
    moves: [{ move: '', date: '', source_url: '' }]
  }])

  useEffect(() => {
    fetchInsights()
    fetchSessions()
  }, [])

  const fetchInsights = async () => {
    try {
      const response = await fetch(`${API_URL}/competitive/insights?limit=50`)
      const data = await response.json()
      setInsights(data)
    } catch (error) {
      console.error('Failed to fetch competitive insights:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchSessions = async () => {
    try {
      const response = await fetch(`${API_URL}/competitive/sessions?limit=10`)
      const data = await response.json()
      setSessions(data)
    } catch (error) {
      console.error('Failed to fetch research sessions:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)

    try {
      let payload: any
      let endpoint: string

      if (mode === 'auto') {
        // Auto mode: minimal fields
        payload = {
          company_name: companyName,
          market_scope: marketScope,
        }
        // Add competitor_names if provided
        if (competitorNames.trim()) {
          payload.competitor_names = competitorNames.split(',').map(name => name.trim()).filter(name => name)
        }
        endpoint = `${API_URL}/competitive/process-auto`
      } else {
        // Manual mode: full fields
        payload = {
          company_name: companyName,
          market_scope: marketScope,
          target_personas: targetPersonas.filter(p => p.trim() !== ''),
          geo_segments: geoSegments.filter(g => g.trim() !== ''),
          competitor_data: competitors.map(comp => ({
            name: comp.name,
            description: comp.description,
            moves: comp.moves.filter(m => m.move.trim() !== '')
          })),
          time_window_months: "12"
        }
        endpoint = `${API_URL}/competitive/process-manual`
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        throw new Error('Failed to process competitive intelligence')
      }

      const result = await response.json()
      alert(`Research session created! Generated ${result.insights_generated?.length || 0} insights.`)

      // Reset form
      setShowForm(false)
      setCompanyName('')
      setMarketScope('')
      setCompetitorNames('')
      setTargetPersonas([''])
      setGeoSegments([''])
      setCompetitors([{ name: '', description: '', moves: [{ move: '', date: '', source_url: '' }] }])

      // Refresh data
      fetchInsights()
      fetchSessions()
    } catch (error) {
      console.error('Failed to submit competitive intelligence:', error)
      alert('Failed to process competitive intelligence. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const addPersona = () => setTargetPersonas([...targetPersonas, ''])
  const removePersona = (index: number) => setTargetPersonas(targetPersonas.filter((_, i) => i !== index))
  const updatePersona = (index: number, value: string) => {
    const updated = [...targetPersonas]
    updated[index] = value
    setTargetPersonas(updated)
  }

  const addGeoSegment = () => setGeoSegments([...geoSegments, ''])
  const removeGeoSegment = (index: number) => setGeoSegments(geoSegments.filter((_, i) => i !== index))
  const updateGeoSegment = (index: number, value: string) => {
    const updated = [...geoSegments]
    updated[index] = value
    setGeoSegments(updated)
  }

  const addCompetitor = () => setCompetitors([...competitors, {
    name: '',
    description: '',
    moves: [{ move: '', date: '', source_url: '' }]
  }])
  const removeCompetitor = (index: number) => setCompetitors(competitors.filter((_, i) => i !== index))
  const updateCompetitor = (index: number, field: keyof CompetitorInput, value: any) => {
    const updated = [...competitors]
    updated[index] = { ...updated[index], [field]: value }
    setCompetitors(updated)
  }

  const addMove = (compIndex: number) => {
    const updated = [...competitors]
    updated[compIndex].moves.push({ move: '', date: '', source_url: '' })
    setCompetitors(updated)
  }
  const removeMove = (compIndex: number, moveIndex: number) => {
    const updated = [...competitors]
    updated[compIndex].moves = updated[compIndex].moves.filter((_, i) => i !== moveIndex)
    setCompetitors(updated)
  }
  const updateMove = (compIndex: number, moveIndex: number, field: keyof CompetitorMove, value: string) => {
    const updated = [...competitors]
    updated[compIndex].moves[moveIndex] = {
      ...updated[compIndex].moves[moveIndex],
      [field]: value
    }
    setCompetitors(updated)
  }

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-100">Competitive Intelligence</h1>
            <p className="text-sm text-gray-400 mt-1">Track competitor moves and strategic insights</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium transition-colors"
          >
            {showForm ? 'Cancel' : '+ Add Competitor Data'}
          </button>
        </div>

        {/* Data Entry Form */}
        {showForm && (
          <div className="bg-[#252526] border border-[#3e3e42] rounded-lg p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">Competitive Research</h2>

            {/* Mode Toggle */}
            <div className="mb-6">
              <div className="flex items-center gap-2 bg-[#1e1e1e] rounded-lg p-1 w-fit">
                <button
                  type="button"
                  onClick={() => setMode('auto')}
                  className={`px-4 py-2 rounded transition-colors ${
                    mode === 'auto'
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-gray-300'
                  }`}
                >
                  Auto
                </button>
                <button
                  type="button"
                  onClick={() => setMode('manual')}
                  className={`px-4 py-2 rounded transition-colors ${
                    mode === 'manual'
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-gray-300'
                  }`}
                >
                  Manual
                </button>
              </div>
              {mode === 'auto' && (
                <p className="text-sm text-gray-400 mt-2">
                  AI will automatically identify competitors, research their recent moves, and generate actionable insights
                </p>
              )}
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Company Context - Always shown */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Your Company Name
                  </label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="w-full px-3 py-2 bg-[#3e3e42] border border-[#4e4e52] rounded text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Market Scope
                  </label>
                  <input
                    type="text"
                    value={marketScope}
                    onChange={(e) => setMarketScope(e.target.value)}
                    placeholder="e.g., B2B sales intelligence"
                    className="w-full px-3 py-2 bg-[#3e3e42] border border-[#4e4e52] rounded text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>

              {/* Auto Mode: Competitor Names (Optional) */}
              {mode === 'auto' && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Competitor Names (Optional)
                  </label>
                  <input
                    type="text"
                    value={competitorNames}
                    onChange={(e) => setCompetitorNames(e.target.value)}
                    placeholder="Leave empty for AI to identify competitors, or enter comma-separated names"
                    className="w-full px-3 py-2 bg-[#3e3e42] border border-[#4e4e52] rounded text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    E.g., Salesforce, HubSpot, Outreach
                  </p>
                </div>
              )}

              {/* Manual Mode: Target Personas */}
              {mode === 'manual' && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Target Personas
                </label>
                {targetPersonas.map((persona, index) => (
                  <div key={index} className="flex gap-2 mb-2">
                    <input
                      type="text"
                      value={persona}
                      onChange={(e) => updatePersona(index, e.target.value)}
                      placeholder="e.g., SDR, AE, RevOps"
                      className="flex-1 px-3 py-2 bg-[#3e3e42] border border-[#4e4e52] rounded text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    {targetPersonas.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removePersona(index)}
                        className="px-3 py-2 bg-red-600 hover:bg-red-700 rounded text-sm"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addPersona}
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  + Add Persona
                </button>
              </div>
              )}

              {/* Manual Mode: Geo Segments */}
              {mode === 'manual' && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Geo Segments
                </label>
                {geoSegments.map((segment, index) => (
                  <div key={index} className="flex gap-2 mb-2">
                    <input
                      type="text"
                      value={segment}
                      onChange={(e) => updateGeoSegment(index, e.target.value)}
                      placeholder="e.g., NA, EU, SMB, ENT"
                      className="flex-1 px-3 py-2 bg-[#3e3e42] border border-[#4e4e52] rounded text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    {geoSegments.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeGeoSegment(index)}
                        className="px-3 py-2 bg-red-600 hover:bg-red-700 rounded text-sm"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addGeoSegment}
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  + Add Segment
                </button>
              </div>
              )}

              {/* Manual Mode: Competitors */}
              {mode === 'manual' && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Competitor Data
                </label>
                {competitors.map((comp, compIndex) => (
                  <div key={compIndex} className="bg-[#1e1e1e] border border-[#3e3e42] rounded p-4 mb-4">
                    <div className="flex justify-between items-center mb-3">
                      <h3 className="font-medium text-gray-200">Competitor {compIndex + 1}</h3>
                      {competitors.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeCompetitor(compIndex)}
                          className="text-sm text-red-400 hover:text-red-300"
                        >
                          Remove Competitor
                        </button>
                      )}
                    </div>

                    <div className="space-y-3">
                      <input
                        type="text"
                        value={comp.name}
                        onChange={(e) => updateCompetitor(compIndex, 'name', e.target.value)}
                        placeholder="Competitor name"
                        className="w-full px-3 py-2 bg-[#3e3e42] border border-[#4e4e52] rounded text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      />

                      <textarea
                        value={comp.description}
                        onChange={(e) => updateCompetitor(compIndex, 'description', e.target.value)}
                        placeholder="Description / context about this competitor"
                        rows={2}
                        className="w-full px-3 py-2 bg-[#3e3e42] border border-[#4e4e52] rounded text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      />

                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          Recent Moves
                        </label>
                        {comp.moves.map((move, moveIndex) => (
                          <div key={moveIndex} className="bg-[#252526] border border-[#3e3e42] rounded p-3 mb-2">
                            <div className="flex justify-between items-center mb-2">
                              <span className="text-xs text-gray-400">Move {moveIndex + 1}</span>
                              {comp.moves.length > 1 && (
                                <button
                                  type="button"
                                  onClick={() => removeMove(compIndex, moveIndex)}
                                  className="text-xs text-red-400 hover:text-red-300"
                                >
                                  Remove
                                </button>
                              )}
                            </div>
                            <div className="space-y-2">
                              <textarea
                                value={move.move}
                                onChange={(e) => updateMove(compIndex, moveIndex, 'move', e.target.value)}
                                placeholder="Describe the competitor move"
                                rows={2}
                                className="w-full px-3 py-2 bg-[#3e3e42] border border-[#4e4e52] rounded text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                required
                              />
                              <div className="grid grid-cols-2 gap-2">
                                <input
                                  type="date"
                                  value={move.date}
                                  onChange={(e) => updateMove(compIndex, moveIndex, 'date', e.target.value)}
                                  className="px-3 py-2 bg-[#3e3e42] border border-[#4e4e52] rounded text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                  required
                                />
                                <input
                                  type="url"
                                  value={move.source_url}
                                  onChange={(e) => updateMove(compIndex, moveIndex, 'source_url', e.target.value)}
                                  placeholder="Source URL"
                                  className="px-3 py-2 bg-[#3e3e42] border border-[#4e4e52] rounded text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                  required
                                />
                              </div>
                            </div>
                          </div>
                        ))}
                        <button
                          type="button"
                          onClick={() => addMove(compIndex)}
                          className="text-xs text-blue-400 hover:text-blue-300"
                        >
                          + Add Move
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addCompetitor}
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  + Add Competitor
                </button>
              </div>
              )}

              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded font-medium transition-colors"
                >
                  {submitting ? 'Processing...' : 'Generate Insights'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-6 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] rounded font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Recent Research Sessions */}
        {sessions.length > 0 && (
          <div className="mb-6">
            <h2 className="text-lg font-semibold mb-3">Recent Research Sessions</h2>
            <div className="space-y-2">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className="bg-[#252526] border border-[#3e3e42] rounded p-4 flex items-center justify-between"
                >
                  <div>
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-gray-200">{session.company_name}</span>
                      <span className="text-xs px-2 py-1 rounded bg-[#3e3e42] text-gray-300">
                        {session.market_scope}
                      </span>
                      <span className={`text-xs px-2 py-1 rounded ${
                        session.status === 'completed' ? 'bg-green-700 text-green-100' :
                        session.status === 'failed' ? 'bg-red-700 text-red-100' :
                        'bg-yellow-700 text-yellow-100'
                      }`}>
                        {session.status}
                      </span>
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {session.competitors_researched.join(', ')} • {session.insights_generated?.length || 0} insights
                    </div>
                  </div>
                  <div className="text-xs text-gray-500">
                    {new Date(session.started_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Competitive Insights */}
        {loading ? (
          <div className="text-center py-12">
            <div className="text-gray-400">Loading competitive insights...</div>
          </div>
        ) : insights.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-2">No competitive insights yet</div>
            <div className="text-sm text-gray-500">Add competitor data to generate insights</div>
          </div>
        ) : (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold mb-3">Competitive Insights ({insights.length})</h2>
            {insights.map((insight) => (
              <div
                key={insight.id}
                className="bg-[#252526] border border-[#3e3e42] rounded-lg hover:border-[#4e4e52] transition-colors cursor-pointer"
                onClick={() => setExpandedInsight(expandedInsight === insight.id ? null : insight.id)}
              >
                <div className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-base">⚔️</span>
                        <span className="text-sm font-semibold text-blue-400">{insight.competitor_name}</span>
                      </div>
                      <h3 className="text-base font-medium text-gray-100 mb-2">{insight.title}</h3>
                      <div className="flex flex-wrap gap-2">
                        <span className={`text-xs px-2 py-1 rounded ${SEVERITY_COLORS[insight.severity]}`}>
                          {insight.severity.toUpperCase()}
                        </span>
                        <span className={`text-xs px-2 py-1 rounded ${EFFORT_COLORS[insight.effort]}`}>
                          Effort: {insight.effort}
                        </span>
                        <span className="text-xs px-2 py-1 rounded bg-blue-700 text-blue-100">
                          P-Score: {insight.priority_score}
                        </span>
                        {insight.evidence_count && (
                          <span className="text-xs px-2 py-1 rounded bg-[#3e3e42] text-gray-300">
                            Evidence: {insight.evidence_count}
                          </span>
                        )}
                        {insight.mentions_30d && (
                          <span className="text-xs px-2 py-1 rounded bg-[#3e3e42] text-gray-300">
                            Mentions: {insight.mentions_30d}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {expandedInsight === insight.id && (
                    <div className="mt-4 pt-4 border-t border-[#3e3e42] space-y-4">
                      {insight.description && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-300 mb-1">Description</h4>
                          <p className="text-sm text-gray-400">{insight.description}</p>
                        </div>
                      )}

                      {insight.impact && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-300 mb-1">Impact</h4>
                          <p className="text-sm text-gray-400">{insight.impact}</p>
                        </div>
                      )}

                      {insight.recommendation && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-300 mb-1">Recommendation</h4>
                          <p className="text-sm text-gray-400">{insight.recommendation}</p>
                        </div>
                      )}

                      {insight.competitor_moves && insight.competitor_moves.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-300 mb-2">Competitor Moves</h4>
                          <div className="space-y-2">
                            {insight.competitor_moves.map((move, idx) => (
                              <div key={idx} className="bg-[#1e1e1e] border border-[#3e3e42] rounded p-3">
                                <div className="flex items-start justify-between mb-1">
                                  <p className="text-sm text-gray-300">{move.move}</p>
                                  <span className="text-xs text-gray-500 whitespace-nowrap ml-2">
                                    {new Date(move.date).toLocaleDateString()}
                                  </span>
                                </div>
                                {move.source_url && (
                                  <a
                                    href={move.source_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs text-blue-400 hover:text-blue-300"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    Source →
                                  </a>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {insight.citations && insight.citations.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-300 mb-2">Citations</h4>
                          <div className="space-y-2">
                            {insight.citations.map((citation, idx) => (
                              <div key={idx} className="bg-[#1e1e1e] border border-[#3e3e42] rounded p-3">
                                <a
                                  href={citation.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sm font-medium text-blue-400 hover:text-blue-300 mb-1 block"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  {citation.title} →
                                </a>
                                <p className="text-xs text-gray-400">{citation.snippet}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {insight.impacted_acv_usd && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-300 mb-1">Financial Impact</h4>
                          <p className="text-sm text-gray-400">
                            Estimated ACV Impact: {insight.impacted_acv_usd}
                            {insight.est_method && <span className="text-xs text-gray-500 ml-2">({insight.est_method})</span>}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}
