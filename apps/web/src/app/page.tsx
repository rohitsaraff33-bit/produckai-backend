'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams, useRouter } from 'next/navigation'
import Layout from '../components/Layout'
import InsightGenerationBanner from '../components/InsightGenerationBanner'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface CustomerInfo {
  id: string
  name: string
  segment: string
  acv: number
}

interface Insight {
  id: string
  title: string
  description?: string
  impact?: string
  recommendation?: string
  severity: string
  effort: string
  priority_score: number
  feedback_count: number
  customers: CustomerInfo[]
  total_acv: number
  metrics?: {
    score: number
    trend: number
    freq_30d: number
    freq_90d: number
    acv_sum: number
    sentiment: number
    dup_penalty: number
  }
}

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

interface InsightDetail extends Insight {
  key_quotes: Feedback[]
  supporting_feedback: Feedback[]
}

const SEVERITY_COLORS: Record<string, string> = {
  low: 'bg-gray-700 text-gray-300',
  medium: 'bg-yellow-600 text-yellow-100',
  high: 'bg-orange-600 text-orange-100',
  critical: 'bg-red-600 text-red-100',
}

const EFFORT_COLORS: Record<string, string> = {
  low: 'bg-green-600 text-green-100',
  medium: 'bg-blue-600 text-blue-100',
  high: 'bg-purple-600 text-purple-100',
}

const SOURCE_ICONS: Record<string, string> = {
  slack: '💬',
  jira: '🎫',
  gdoc: '📄',
  zoom: '🎥',
}

const SOURCE_COLORS: Record<string, string> = {
  slack: 'bg-purple-700 text-purple-200',
  jira: 'bg-blue-700 text-blue-200',
  gdoc: 'bg-green-700 text-green-200',
  zoom: 'bg-orange-700 text-orange-200',
}

type SeverityType = 'critical' | 'high' | 'medium' | 'low'
type SegmentType = 'ENT' | 'MM' | 'SMB'
type EffortType = 'low' | 'medium' | 'high'

export default function InsightsBoard() {
  const [insights, setInsights] = useState<Insight[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedInsight, setExpandedInsight] = useState<string | null>(null)
  const [showChat, setShowChat] = useState(false)
  const [selectedInsightId, setSelectedInsightId] = useState<string | null>(null)
  const [selectedInsightDetail, setSelectedInsightDetail] = useState<InsightDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [prdMarkdown, setPrdMarkdown] = useState<string | null>(null)
  const [loadingPrd, setLoadingPrd] = useState(false)
  const [editedPrdMarkdown, setEditedPrdMarkdown] = useState<string>('')
  const [showAIPrototypeModal, setShowAIPrototypeModal] = useState(false)
  const [aiPrompt, setAIPrompt] = useState('')
  const [recommendedTool, setRecommendedTool] = useState('')
  const [toolReason, setToolReason] = useState('')
  const [loadingAIPrompt, setLoadingAIPrompt] = useState(false)
  const [copiedPrompt, setCopiedPrompt] = useState(false)

  // Filter states
  const [priorityMin, setPriorityMin] = useState<number>(0)
  const [priorityMax, setPriorityMax] = useState<number>(100)
  const [severityFilters, setSeverityFilters] = useState<SeverityType[]>([])
  const [segmentFilters, setSegmentFilters] = useState<SegmentType[]>([])
  const [effortFilters, setEffortFilters] = useState<EffortType[]>([])

  // Popover/Modal states
  const [showPriorityPopover, setShowPriorityPopover] = useState(false)
  const [showSeverityPopover, setShowSeverityPopover] = useState(false)
  const [showMoreFiltersModal, setShowMoreFiltersModal] = useState(false)

  // Temporary states for popovers (before apply)
  const [tempPriorityMin, setTempPriorityMin] = useState<number>(0)
  const [tempPriorityMax, setTempPriorityMax] = useState<number>(100)
  const [tempSeverityFilters, setTempSeverityFilters] = useState<SeverityType[]>([])
  const [tempSegmentFilters, setTempSegmentFilters] = useState<SegmentType[]>([])
  const [tempEffortFilters, setTempEffortFilters] = useState<EffortType[]>([])

  const searchParams = useSearchParams()
  const router = useRouter()
  const selectedCustomer = searchParams.get('customer')
  const selectedFilter = searchParams.get('filter')

  useEffect(() => {
    // Load filters from URL on mount
    const urlPriorityMin = searchParams.get('priority_min')
    const urlPriorityMax = searchParams.get('priority_max')
    const urlSeverity = searchParams.get('severity')
    const urlSegments = searchParams.get('segments')
    const urlEffort = searchParams.get('effort')

    if (urlPriorityMin) setPriorityMin(parseInt(urlPriorityMin))
    if (urlPriorityMax) setPriorityMax(parseInt(urlPriorityMax))
    if (urlSeverity) setSeverityFilters(urlSeverity.split(',') as SeverityType[])
    if (urlSegments) setSegmentFilters(urlSegments.split(',') as SegmentType[])
    if (urlEffort) setEffortFilters(urlEffort.split(',') as EffortType[])
  }, [])

  useEffect(() => {
    fetchInsights()
  }, [selectedCustomer, selectedFilter, priorityMin, priorityMax, severityFilters, segmentFilters, effortFilters])

  useEffect(() => {
    if (selectedInsightId) {
      fetchInsightDetail(selectedInsightId)
    }
  }, [selectedInsightId])

  const updateURLWithFilters = () => {
    const params = new URLSearchParams()

    if (selectedCustomer) params.set('customer', selectedCustomer)
    if (selectedFilter) params.set('filter', selectedFilter)
    if (priorityMin > 0) params.set('priority_min', priorityMin.toString())
    if (priorityMax < 100) params.set('priority_max', priorityMax.toString())
    if (severityFilters.length > 0) params.set('severity', severityFilters.join(','))
    if (segmentFilters.length > 0) params.set('segments', segmentFilters.join(','))
    if (effortFilters.length > 0) params.set('effort', effortFilters.join(','))

    const newURL = params.toString() ? `/?${params.toString()}` : '/'
    router.push(newURL, { scroll: false })
  }

  const fetchInsights = async () => {
    try {
      setLoading(true)

      let data
      if (selectedCustomer) {
        // Fetch insights for specific customer
        const response = await fetch(`${API_URL}/customers/${encodeURIComponent(selectedCustomer)}/insights`)
        const customerData = await response.json()
        data = customerData.insights || []
      } else {
        // Fetch all insights with filters
        let url = `${API_URL}/themes?sort_by=priority&limit=20`
        if (selectedFilter) {
          url += `&filter=${selectedFilter}`
        }
        if (priorityMin > 0) {
          url += `&priority_min=${priorityMin}`
        }
        if (priorityMax < 100) {
          url += `&priority_max=${priorityMax}`
        }
        if (severityFilters.length > 0) {
          severityFilters.forEach(sev => {
            url += `&severity=${sev}`
          })
        }
        if (segmentFilters.length > 0) {
          segmentFilters.forEach(seg => {
            url += `&segments=${seg}`
          })
        }
        if (effortFilters.length > 0) {
          effortFilters.forEach(eff => {
            url += `&effort=${eff}`
          })
        }
        const response = await fetch(url)
        data = await response.json()
      }

      setInsights(data)
    } catch (error) {
      console.error('Failed to fetch insights:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchInsightDetail = async (id: string) => {
    setLoadingDetail(true)
    try {
      const response = await fetch(`${API_URL}/themes/${id}`)
      if (!response.ok) throw new Error('Insight not found')
      const data = await response.json()
      setSelectedInsightDetail(data)
    } catch (error) {
      console.error('Failed to fetch insight detail:', error)
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleViewDetails = (insightId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedInsightId(insightId)
    setShowChat(false) // Close chat when opening details
  }

  const handleCloseDetails = () => {
    setSelectedInsightId(null)
    setSelectedInsightDetail(null)
    setPrdMarkdown(null)
    setEditedPrdMarkdown('')
  }

  const handleDraftPrd = async (insightId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setLoadingPrd(true)
    setPrdMarkdown(null)

    try {
      const response = await fetch(`${API_URL}/themes/${insightId}/generate-prd`)
      if (!response.ok) throw new Error('Failed to generate PRD')
      const data = await response.json()
      setPrdMarkdown(data.prd_markdown)
      setEditedPrdMarkdown(data.prd_markdown)
      setSelectedInsightId(insightId)
      setShowChat(false)
    } catch (error) {
      console.error('Failed to generate PRD:', error)
      alert('Failed to generate PRD. Please try again.')
    } finally {
      setLoadingPrd(false)
    }
  }

  const handleCopyPrd = () => {
    if (editedPrdMarkdown) {
      navigator.clipboard.writeText(editedPrdMarkdown)
      alert('PRD copied to clipboard!')
    }
  }

  const handleDownloadPrd = () => {
    if (editedPrdMarkdown && selectedInsightDetail) {
      const blob = new Blob([editedPrdMarkdown], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `prd-${selectedInsightDetail.title.toLowerCase().replace(/\s+/g, '-')}.md`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }

  const handleBackToDetails = () => {
    setPrdMarkdown(null)
    setEditedPrdMarkdown('')
  }

  const handleAIPrototype = async (insightId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setLoadingAIPrompt(true)

    try {
      const response = await fetch(`${API_URL}/themes/${insightId}/generate-ai-prompt?prototype_type=mvp`)
      if (!response.ok) throw new Error('Failed to generate AI prompt')
      const data = await response.json()
      setAIPrompt(data.prompt || '')
      setRecommendedTool(data.recommended_tool || 'Lovable')
      setToolReason(data.reason || '')
      setShowAIPrototypeModal(true)
    } catch (error) {
      console.error('Failed to generate AI prompt:', error)
      alert('Failed to generate AI prototype prompt. Please try again.')
    } finally {
      setLoadingAIPrompt(false)
    }
  }

  const handleCopyPrompt = () => {
    if (aiPrompt) {
      navigator.clipboard.writeText(aiPrompt)
      setCopiedPrompt(true)
      setTimeout(() => setCopiedPrompt(false), 2000)
    }
  }

  const handleCloseAIPrototypeModal = () => {
    setShowAIPrototypeModal(false)
    setAIPrompt('')
    setRecommendedTool('')
    setToolReason('')
    setCopiedPrompt(false)
  }

  // Filter handlers
  const handleApplyPriority = () => {
    setPriorityMin(tempPriorityMin)
    setPriorityMax(tempPriorityMax)
    setShowPriorityPopover(false)
    updateURLWithFilters()
  }

  const handleClearPriority = () => {
    setTempPriorityMin(0)
    setTempPriorityMax(100)
  }

  const handleApplySeverity = () => {
    setSeverityFilters(tempSeverityFilters)
    setShowSeverityPopover(false)
    updateURLWithFilters()
  }

  const handleClearSeverity = () => {
    setTempSeverityFilters([])
  }

  const toggleTempSeverity = (severity: SeverityType) => {
    if (tempSeverityFilters.includes(severity)) {
      setTempSeverityFilters(tempSeverityFilters.filter(s => s !== severity))
    } else {
      setTempSeverityFilters([...tempSeverityFilters, severity])
    }
  }

  const handleApplyMoreFilters = () => {
    setSegmentFilters(tempSegmentFilters)
    setEffortFilters(tempEffortFilters)
    setShowMoreFiltersModal(false)
    updateURLWithFilters()
  }

  const handleClearMoreFilters = () => {
    setTempSegmentFilters([])
    setTempEffortFilters([])
  }

  const toggleTempSegment = (segment: SegmentType) => {
    if (tempSegmentFilters.includes(segment)) {
      setTempSegmentFilters(tempSegmentFilters.filter(s => s !== segment))
    } else {
      setTempSegmentFilters([...tempSegmentFilters, segment])
    }
  }

  const toggleTempEffort = (effort: EffortType) => {
    if (tempEffortFilters.includes(effort)) {
      setTempEffortFilters(tempEffortFilters.filter(e => e !== effort))
    } else {
      setTempEffortFilters([...tempEffortFilters, effort])
    }
  }

  const handleClearAllFilters = () => {
    setPriorityMin(0)
    setPriorityMax(100)
    setSeverityFilters([])
    setSegmentFilters([])
    setEffortFilters([])
    router.push('/')
  }

  const removePriorityFilter = () => {
    setPriorityMin(0)
    setPriorityMax(100)
    updateURLWithFilters()
  }

  const removeSeverityChip = (severity: SeverityType) => {
    setSeverityFilters(severityFilters.filter(s => s !== severity))
    updateURLWithFilters()
  }

  const removeSegmentChip = (segment: SegmentType) => {
    setSegmentFilters(segmentFilters.filter(s => s !== segment))
    updateURLWithFilters()
  }

  const removeEffortChip = (effort: EffortType) => {
    setEffortFilters(effortFilters.filter(e => e !== effort))
    updateURLWithFilters()
  }

  const setPriorityPreset = (min: number, max: number) => {
    setTempPriorityMin(min)
    setTempPriorityMax(max)
  }

  // Open popovers with current values
  const openPriorityPopover = () => {
    setTempPriorityMin(priorityMin)
    setTempPriorityMax(priorityMax)
    setShowPriorityPopover(true)
  }

  const openSeverityPopover = () => {
    setTempSeverityFilters([...severityFilters])
    setShowSeverityPopover(true)
  }

  const openMoreFiltersModal = () => {
    setTempSegmentFilters([...segmentFilters])
    setTempEffortFilters([...effortFilters])
    setShowMoreFiltersModal(true)
  }

  // Check if any filters are active
  const hasActiveFilters = priorityMin > 0 || priorityMax < 100 || severityFilters.length > 0 || segmentFilters.length > 0 || effortFilters.length > 0

  if (loading) {
    return (
      <Layout showChat={showChat} onChatToggle={() => setShowChat(!showChat)} selectedInsightId={selectedInsightId}>
        <div className="flex items-center justify-center h-full">
          <div className="text-lg">Loading insights...</div>
        </div>
      </Layout>
    )
  }

  // Filter display names
  const filterNames: Record<string, string> = {
    enterprise_blockers: 'Enterprise Blockers',
    high_priority: 'High Priority',
    trending: 'Trending',
  }

  return (
    <Layout showChat={showChat} onChatToggle={() => setShowChat(!showChat)} selectedInsightId={selectedInsightId}>
      <InsightGenerationBanner />
      <div className="max-w-6xl mx-auto px-6 py-6">
        {/* Filter Indicators */}
        {(selectedCustomer || selectedFilter) && (
          <div className="mb-4 flex items-center gap-3 p-3 bg-blue-900/20 border border-blue-500/30 rounded">
            {selectedCustomer && (
              <span className="text-sm text-gray-300">
                Customer: <span className="font-semibold text-blue-400">{selectedCustomer}</span>
              </span>
            )}
            {selectedFilter && (
              <span className="text-sm text-gray-300">
                Filter: <span className="font-semibold text-blue-400">{filterNames[selectedFilter] || selectedFilter}</span>
              </span>
            )}
            <button
              onClick={() => router.push('/')}
              className="ml-auto px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs font-medium transition-colors"
            >
              Clear All Filters
            </button>
          </div>
        )}

        {/* Top Header Filters */}
        <div className="mb-4">
          <div className="flex items-center gap-3 mb-3">
            {/* Priority Button */}
            <div className="relative">
              <button
                onClick={openPriorityPopover}
                className="px-4 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] rounded text-sm font-medium transition-colors flex items-center gap-2"
              >
                Priority {(priorityMin > 0 || priorityMax < 100) && <span className="text-blue-400">•</span>}
                <span className="text-gray-400">▾</span>
              </button>

              {/* Priority Popover */}
              {showPriorityPopover && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setShowPriorityPopover(false)}></div>
                  <div className="absolute top-full mt-2 left-0 w-80 bg-[#252526] border border-[#3e3e42] rounded-lg shadow-xl z-50 p-4">
                    <h3 className="text-sm font-semibold text-gray-200 mb-3">Priority Range</h3>

                    {/* Range Display */}
                    <div className="mb-4 text-center">
                      <span className="text-2xl font-bold text-blue-400">{tempPriorityMin}</span>
                      <span className="text-gray-500 mx-2">-</span>
                      <span className="text-2xl font-bold text-blue-400">{tempPriorityMax}</span>
                    </div>

                    {/* Dual Range Slider */}
                    <div className="mb-4 px-2">
                      <div className="relative h-8">
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={tempPriorityMin}
                          onChange={(e) => {
                            const val = parseInt(e.target.value)
                            if (val <= tempPriorityMax) setTempPriorityMin(val)
                          }}
                          className="absolute w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                          style={{ zIndex: tempPriorityMin > 50 ? 2 : 1 }}
                        />
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={tempPriorityMax}
                          onChange={(e) => {
                            const val = parseInt(e.target.value)
                            if (val >= tempPriorityMin) setTempPriorityMax(val)
                          }}
                          className="absolute w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                          style={{ zIndex: tempPriorityMax > 50 ? 2 : 1 }}
                        />
                      </div>
                    </div>

                    {/* Quick Presets */}
                    <div className="space-y-2 mb-4">
                      <button
                        onClick={() => setPriorityPreset(80, 100)}
                        className="w-full px-3 py-2 bg-red-900/30 hover:bg-red-900/50 border border-red-500/30 rounded text-xs text-left transition-colors"
                      >
                        <span className="font-medium text-red-400">P0: Critical</span>
                        <span className="text-gray-400 ml-2">(80-100)</span>
                      </button>
                      <button
                        onClick={() => setPriorityPreset(60, 79)}
                        className="w-full px-3 py-2 bg-orange-900/30 hover:bg-orange-900/50 border border-orange-500/30 rounded text-xs text-left transition-colors"
                      >
                        <span className="font-medium text-orange-400">P1: High</span>
                        <span className="text-gray-400 ml-2">(60-79)</span>
                      </button>
                      <button
                        onClick={() => setPriorityPreset(40, 59)}
                        className="w-full px-3 py-2 bg-yellow-900/30 hover:bg-yellow-900/50 border border-yellow-500/30 rounded text-xs text-left transition-colors"
                      >
                        <span className="font-medium text-yellow-400">P2: Medium</span>
                        <span className="text-gray-400 ml-2">(40-59)</span>
                      </button>
                      <button
                        onClick={() => setPriorityPreset(0, 39)}
                        className="w-full px-3 py-2 bg-gray-700/30 hover:bg-gray-700/50 border border-gray-500/30 rounded text-xs text-left transition-colors"
                      >
                        <span className="font-medium text-gray-400">P3: Low</span>
                        <span className="text-gray-400 ml-2">(0-39)</span>
                      </button>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-3 border-t border-[#3e3e42]">
                      <button
                        onClick={handleClearPriority}
                        className="flex-1 px-3 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] rounded text-xs font-medium transition-colors"
                      >
                        Clear
                      </button>
                      <button
                        onClick={handleApplyPriority}
                        className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded text-xs font-medium transition-colors"
                      >
                        Apply
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Severity Button */}
            <div className="relative">
              <button
                onClick={openSeverityPopover}
                className="px-4 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] rounded text-sm font-medium transition-colors flex items-center gap-2"
              >
                Severity {severityFilters.length > 0 && <span className="text-blue-400">•</span>}
                <span className="text-gray-400">▾</span>
              </button>

              {/* Severity Popover */}
              {showSeverityPopover && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setShowSeverityPopover(false)}></div>
                  <div className="absolute top-full mt-2 left-0 w-64 bg-[#252526] border border-[#3e3e42] rounded-lg shadow-xl z-50 p-4">
                    <h3 className="text-sm font-semibold text-gray-200 mb-3">Severity</h3>

                    {/* Severity Checkboxes */}
                    <div className="space-y-2 mb-4">
                      {(['critical', 'high', 'medium', 'low'] as SeverityType[]).map(severity => (
                        <label key={severity} className="flex items-center gap-3 cursor-pointer hover:bg-[#3e3e42] p-2 rounded transition-colors">
                          <input
                            type="checkbox"
                            checked={tempSeverityFilters.includes(severity)}
                            onChange={() => toggleTempSeverity(severity)}
                            className="w-4 h-4 rounded border-gray-600 bg-[#1e1e1e] text-blue-600 focus:ring-blue-500 focus:ring-offset-0"
                          />
                          <span className="text-sm text-gray-300 capitalize">{severity}</span>
                        </label>
                      ))}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-3 border-t border-[#3e3e42]">
                      <button
                        onClick={handleClearSeverity}
                        className="flex-1 px-3 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] rounded text-xs font-medium transition-colors"
                      >
                        Clear
                      </button>
                      <button
                        onClick={handleApplySeverity}
                        className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded text-xs font-medium transition-colors"
                      >
                        Apply
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* More Filters Button */}
            <div className="relative">
              <button
                onClick={openMoreFiltersModal}
                className="px-4 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] rounded text-sm font-medium transition-colors flex items-center gap-2"
              >
                More Filters {(segmentFilters.length > 0 || effortFilters.length > 0) && <span className="text-blue-400">•</span>}
                <span className="text-gray-400">▾</span>
              </button>
            </div>
          </div>

          {/* Active Filter Chips */}
          {hasActiveFilters && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-gray-400">Active:</span>

              {/* Priority Chip */}
              {(priorityMin > 0 || priorityMax < 100) && (
                <div className="flex items-center gap-1 px-2 py-1 bg-blue-900/30 border border-blue-500/30 rounded text-xs">
                  <span className="text-blue-300">P{priorityMin}-P{priorityMax}</span>
                  <button
                    onClick={removePriorityFilter}
                    className="ml-1 text-blue-400 hover:text-blue-200"
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* Severity Chips */}
              {severityFilters.map(severity => (
                <div key={severity} className="flex items-center gap-1 px-2 py-1 bg-orange-900/30 border border-orange-500/30 rounded text-xs">
                  <span className="text-orange-300 capitalize">{severity}</span>
                  <button
                    onClick={() => removeSeverityChip(severity)}
                    className="ml-1 text-orange-400 hover:text-orange-200"
                  >
                    ✕
                  </button>
                </div>
              ))}

              {/* Segment Chips */}
              {segmentFilters.map(segment => (
                <div key={segment} className="flex items-center gap-1 px-2 py-1 bg-purple-900/30 border border-purple-500/30 rounded text-xs">
                  <span className="text-purple-300">{segment === 'ENT' ? 'Enterprise' : segment === 'MM' ? 'Mid-Market' : 'SMB'}</span>
                  <button
                    onClick={() => removeSegmentChip(segment)}
                    className="ml-1 text-purple-400 hover:text-purple-200"
                  >
                    ✕
                  </button>
                </div>
              ))}

              {/* Effort Chips */}
              {effortFilters.map(effort => (
                <div key={effort} className="flex items-center gap-1 px-2 py-1 bg-green-900/30 border border-green-500/30 rounded text-xs">
                  <span className="text-green-300 capitalize">{effort} Effort</span>
                  <button
                    onClick={() => removeEffortChip(effort)}
                    className="ml-1 text-green-400 hover:text-green-200"
                  >
                    ✕
                  </button>
                </div>
              ))}

              {/* Clear All */}
              <button
                onClick={handleClearAllFilters}
                className="px-2 py-1 text-xs text-gray-400 hover:text-gray-200 underline"
              >
                Clear all
              </button>
            </div>
          )}
        </div>

        {/* Insights List */}
        {insights.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p>No insights found. Run clustering to generate insights.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {insights.map((insight) => {
              const isExpanded = expandedInsight === insight.id
              const severityColor = SEVERITY_COLORS[insight.severity] || SEVERITY_COLORS.medium
              const effortColor = EFFORT_COLORS[insight.effort] || EFFORT_COLORS.medium

              return (
                <div
                  key={insight.id}
                  className="bg-[#252526] border border-[#3e3e42] rounded-lg overflow-hidden hover:border-[#5e5e62] transition-colors"
                >
                  {/* Card Header - Always Visible */}
                  <div
                    className="p-4 cursor-pointer"
                    onClick={() => setExpandedInsight(isExpanded ? null : insight.id)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start gap-2 mb-2">
                          <button className="text-gray-400 hover:text-gray-200 mt-0.5">
                            {isExpanded ? '▼' : '▶'}
                          </button>
                          <h3 className="text-base font-medium text-gray-100 flex-1">
                            {insight.title}
                          </h3>
                        </div>
                        <p className="text-sm text-gray-400 ml-6 line-clamp-2">
                          {insight.description || 'No description available'}
                        </p>

                        {/* Customer Information */}
                        {insight.customers && insight.customers.length > 0 && (
                          <div className="ml-6 mt-2 flex items-center gap-2 text-xs">
                            <span className="text-gray-500">Affecting:</span>
                            <div className="flex items-center gap-2 flex-wrap">
                              {insight.customers.map((customer, idx) => (
                                <span
                                  key={customer.id}
                                  className={`px-2 py-0.5 rounded ${
                                    customer.segment === 'ENT'
                                      ? 'bg-purple-900/40 text-purple-300'
                                      : customer.segment === 'MM'
                                      ? 'bg-blue-900/40 text-blue-300'
                                      : 'bg-gray-700/40 text-gray-300'
                                  }`}
                                  title={`${customer.segment} • $${(customer.acv / 1000).toFixed(0)}k ACV`}
                                >
                                  {customer.name} (${(customer.acv / 1000).toFixed(0)}k)
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Badges */}
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${severityColor}`}
                          title="Severity: Customer & business impact level (Critical/High/Medium/Low based on ACV, customer type, and frequency)"
                        >
                          SEVERITY: {insight.severity.toUpperCase()}
                        </span>
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${effortColor}`}
                          title="Effort: Estimated engineering effort (Low: <1 week, Medium: 1-4 weeks, High: >1 month)"
                        >
                          EFFORT: {insight.effort.length <= 3 ? insight.effort.toUpperCase() : insight.effort.substring(0, 3).toUpperCase()}
                        </span>
                        <span
                          className="px-2 py-1 rounded text-xs font-medium bg-blue-600 text-blue-100 flex items-center gap-1"
                          title="Priority Score (0-100): Calculated from severity, effort, ACV, frequency, trend, and sentiment. Higher score = higher priority."
                        >
                          P{insight.priority_score} <span className="text-[10px] opacity-70">ℹ️</span>
                        </span>
                      </div>
                    </div>

                    {/* Quick Stats */}
                    <div className="flex items-center gap-4 ml-6 mt-3 text-xs text-gray-400">
                      <span>{insight.feedback_count} evidence items</span>
                      {insight.metrics && (
                        <>
                          <span>•</span>
                          <span>{insight.metrics.freq_30d} mentions (30d)</span>
                          <span>•</span>
                          <span>${(insight.metrics.acv_sum / 1000).toFixed(0)}k ACV</span>
                          {insight.metrics.trend > 0 && (
                            <>
                              <span>•</span>
                              <span className="text-green-400">↗ Trending</span>
                            </>
                          )}
                        </>
                      )}
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && (
                    <div className="border-t border-[#3e3e42] bg-[#1e1e1e]">
                      {/* Impact & Recommendation */}
                      <div className="p-4 grid md:grid-cols-2 gap-4">
                        {insight.impact && (
                          <div className="bg-[#2d2d30] p-3 rounded border-l-2 border-orange-500">
                            <div className="text-xs font-semibold text-orange-400 mb-1">💥 IMPACT</div>
                            <p className="text-sm text-gray-300">{insight.impact}</p>
                          </div>
                        )}
                        {insight.recommendation && (
                          <div className="bg-[#2d2d30] p-3 rounded border-l-2 border-green-500">
                            <div className="text-xs font-semibold text-green-400 mb-1">✅ RECOMMENDATION</div>
                            <p className="text-sm text-gray-300 whitespace-pre-line">{insight.recommendation}</p>
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="px-4 pb-4 flex items-center gap-2">
                        <button
                          onClick={(e) => handleViewDetails(insight.id, e)}
                          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium transition-colors"
                        >
                          View Details
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setShowChat(true)
                            setSelectedInsightId(null) // Close details when opening chat
                          }}
                          className="px-4 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] rounded text-sm font-medium transition-colors"
                        >
                          Ask AI Assistant
                        </button>
                        <button className="px-4 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] rounded text-sm font-medium transition-colors">
                          Create JIRA
                        </button>
                        <button
                          onClick={(e) => handleAIPrototype(insight.id, e)}
                          disabled={loadingAIPrompt}
                          className="px-4 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm font-medium transition-colors"
                        >
                          {loadingAIPrompt ? 'Generating...' : '🚀 AI Prototype'}
                        </button>
                        <button
                          onClick={(e) => handleDraftPrd(insight.id, e)}
                          disabled={loadingPrd}
                          className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm font-medium transition-colors"
                        >
                          {loadingPrd ? 'Generating...' : 'Draft PRD'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* More Filters Modal */}
      {showMoreFiltersModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-[#252526] border border-[#3e3e42] rounded-lg w-full max-w-md shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#3e3e42]">
              <h2 className="text-lg font-semibold text-gray-100">More Filters</h2>
              <button
                onClick={() => setShowMoreFiltersModal(false)}
                className="p-1 hover:bg-[#3e3e42] rounded text-gray-400 hover:text-gray-200 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Content */}
            <div className="px-6 py-4 space-y-6">
              {/* Customer Segment */}
              <div>
                <h3 className="text-sm font-semibold text-gray-200 mb-3">Customer Segment</h3>
                <div className="space-y-2">
                  {(['ENT', 'MM', 'SMB'] as SegmentType[]).map(segment => (
                    <label key={segment} className="flex items-center gap-3 cursor-pointer hover:bg-[#3e3e42] p-2 rounded transition-colors">
                      <input
                        type="checkbox"
                        checked={tempSegmentFilters.includes(segment)}
                        onChange={() => toggleTempSegment(segment)}
                        className="w-4 h-4 rounded border-gray-600 bg-[#1e1e1e] text-blue-600 focus:ring-blue-500 focus:ring-offset-0"
                      />
                      <span className="text-sm text-gray-300">
                        {segment === 'ENT' ? 'Enterprise' : segment === 'MM' ? 'Mid-Market' : 'SMB'}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Effort */}
              <div>
                <h3 className="text-sm font-semibold text-gray-200 mb-3">Effort</h3>
                <div className="space-y-2">
                  {(['low', 'medium', 'high'] as EffortType[]).map(effort => (
                    <label key={effort} className="flex items-center gap-3 cursor-pointer hover:bg-[#3e3e42] p-2 rounded transition-colors">
                      <input
                        type="checkbox"
                        checked={tempEffortFilters.includes(effort)}
                        onChange={() => toggleTempEffort(effort)}
                        className="w-4 h-4 rounded border-gray-600 bg-[#1e1e1e] text-blue-600 focus:ring-blue-500 focus:ring-offset-0"
                      />
                      <span className="text-sm text-gray-300 capitalize">{effort}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-[#3e3e42] flex justify-between">
              <button
                onClick={handleClearMoreFilters}
                className="px-4 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] rounded text-sm font-medium transition-colors"
              >
                Clear All
              </button>
              <button
                onClick={handleApplyMoreFilters}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium transition-colors"
              >
                Apply Filters
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Detail Panel */}
      {selectedInsightId && (
        <aside className="fixed right-0 top-0 h-screen w-[600px] bg-[#252526] border-l border-[#3e3e42] flex flex-col shadow-2xl z-50 overflow-hidden">
          {/* Header */}
          <div className="h-14 flex items-center justify-between px-4 border-b border-[#3e3e42] flex-shrink-0">
            <div className="flex items-center gap-2">
              {prdMarkdown && (
                <button
                  onClick={handleBackToDetails}
                  className="p-1 hover:bg-[#3e3e42] rounded text-gray-400 hover:text-gray-200"
                  title="Back to Details"
                >
                  ←
                </button>
              )}
              <h3 className="font-semibold text-sm">
                {prdMarkdown ? 'PRD Editor' : 'Insight Details'}
              </h3>
            </div>
            <button
              onClick={handleCloseDetails}
              className="p-1 hover:bg-[#3e3e42] rounded text-gray-400 hover:text-gray-200"
            >
              ✕
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            {loadingPrd ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-sm text-gray-400">Generating PRD...</div>
              </div>
            ) : prdMarkdown ? (
              <div className="flex flex-col h-full">
                {/* PRD Editor Toolbar */}
                <div className="flex items-center gap-2 p-3 border-b border-[#3e3e42] bg-[#1e1e1e] flex-shrink-0">
                  <button
                    onClick={handleCopyPrd}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-xs font-medium transition-colors"
                  >
                    📋 Copy
                  </button>
                  <button
                    onClick={handleDownloadPrd}
                    className="px-3 py-1.5 bg-green-600 hover:bg-green-700 rounded text-xs font-medium transition-colors"
                  >
                    ⬇️ Download
                  </button>
                  <span className="text-xs text-gray-500 ml-auto">
                    Edit below to customize
                  </span>
                </div>

                {/* PRD Editor */}
                <div className="flex-1 overflow-hidden p-4">
                  <textarea
                    value={editedPrdMarkdown}
                    onChange={(e) => setEditedPrdMarkdown(e.target.value)}
                    className="w-full h-full bg-[#1e1e1e] text-gray-300 p-4 rounded border border-[#3e3e42] focus:outline-none focus:border-blue-500 font-mono text-sm resize-none"
                    placeholder="PRD content will appear here..."
                  />
                </div>
              </div>
            ) : loadingDetail ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-sm text-gray-400">Loading details...</div>
              </div>
            ) : selectedInsightDetail ? (
              <div className="p-6">
                {/* Title & Badges */}
                <div className="mb-6">
                  <h2 className="text-xl font-bold text-gray-100 mb-3">{selectedInsightDetail.title}</h2>
                  <div className="flex items-center gap-2 mb-4">
                    <span
                      className={`px-3 py-1 rounded text-xs font-medium ${SEVERITY_COLORS[selectedInsightDetail.severity] || SEVERITY_COLORS.medium}`}
                      title="Severity: Customer & business impact level (Critical/High/Medium/Low based on ACV, customer type, and frequency)"
                    >
                      SEVERITY: {selectedInsightDetail.severity.toUpperCase()}
                    </span>
                    <span
                      className={`px-3 py-1 rounded text-xs font-medium ${EFFORT_COLORS[selectedInsightDetail.effort] || EFFORT_COLORS.medium}`}
                      title="Effort: Estimated engineering effort (Low: <1 week, Medium: 1-4 weeks, High: >1 month)"
                    >
                      EFFORT: {selectedInsightDetail.effort.length <= 3 ? selectedInsightDetail.effort.toUpperCase() : selectedInsightDetail.effort.substring(0, 3).toUpperCase()}
                    </span>
                    <span
                      className="px-3 py-1 rounded text-xs font-medium bg-blue-600 text-blue-100 flex items-center gap-1"
                      title="Priority Score (0-100): Calculated from severity, effort, ACV, frequency, trend, and sentiment. Higher score = higher priority."
                    >
                      P{selectedInsightDetail.priority_score} <span className="text-[10px] opacity-70">ℹ️</span>
                    </span>
                  </div>
                  {selectedInsightDetail.description && (
                    <p className="text-sm text-gray-300 mb-4">{selectedInsightDetail.description}</p>
                  )}
                </div>

                {/* Impact & Recommendation */}
                <div className="space-y-4 mb-6">
                  {selectedInsightDetail.impact && (
                    <div className="bg-[#2d2d30] p-4 rounded border-l-4 border-orange-500">
                      <div className="text-xs font-semibold text-orange-400 mb-2">💥 IMPACT</div>
                      <p className="text-sm text-gray-300">{selectedInsightDetail.impact}</p>
                    </div>
                  )}
                  {selectedInsightDetail.recommendation && (
                    <div className="bg-[#2d2d30] p-4 rounded border-l-4 border-green-500">
                      <div className="text-xs font-semibold text-green-400 mb-2">✅ RECOMMENDATION</div>
                      <p className="text-sm text-gray-300 whitespace-pre-line">{selectedInsightDetail.recommendation}</p>
                    </div>
                  )}
                </div>

                {/* Metrics */}
                {selectedInsightDetail.metrics && (() => {
                  const score = Math.round(selectedInsightDetail.metrics.score * 100)
                  const severityScore = {'low': 25, 'medium': 50, 'high': 75, 'critical': 100}[selectedInsightDetail.severity] || 50
                  const effortScore = {'low': 75, 'medium': 50, 'high': 25}[selectedInsightDetail.effort] || 50
                  const acvScore = Math.min(20, (selectedInsightDetail.metrics.acv_sum / 100000) * 2)
                  const freqScore = Math.min(10, selectedInsightDetail.metrics.freq_30d * 2)
                  const trendScore = selectedInsightDetail.metrics.trend > 0 ? 10 : 5

                  // Priority tier
                  const priorityTier = score >= 80 ? { label: 'P0 - Critical', color: 'text-red-400', bg: 'bg-red-900/40', border: 'border-red-500', action: 'Address immediately' }
                    : score >= 60 ? { label: 'P1 - High', color: 'text-orange-400', bg: 'bg-orange-900/40', border: 'border-orange-500', action: 'Prioritize for next sprint' }
                    : score >= 40 ? { label: 'P2 - Medium', color: 'text-yellow-400', bg: 'bg-yellow-900/40', border: 'border-yellow-500', action: 'Plan for next quarter' }
                    : { label: 'P3 - Low', color: 'text-gray-400', bg: 'bg-gray-700/40', border: 'border-gray-500', action: 'Add to backlog' }

                  // Customer breakdown
                  const customerCount = selectedInsightDetail.customers?.length || 0
                  const entCount = selectedInsightDetail.customers?.filter((c: any) => c.segment === 'ENT').length || 0
                  const mmCount = selectedInsightDetail.customers?.filter((c: any) => c.segment === 'MM').length || 0
                  const smbCount = selectedInsightDetail.customers?.filter((c: any) => c.segment === 'SMB').length || 0

                  return (
                    <div className="bg-[#1e1e1e] rounded-lg p-4 mb-6">
                      <h3 className="text-sm font-semibold text-gray-200 mb-3">Priority Score & Impact</h3>

                      {/* Priority Tier Banner */}
                      <div className={`${priorityTier.bg} ${priorityTier.border} border-l-4 p-3 rounded mb-4`}>
                        <div className="flex items-center justify-between">
                          <div>
                            <div className={`text-lg font-bold ${priorityTier.color}`}>{priorityTier.label}</div>
                            <div className="text-xs text-gray-400 mt-1">Action: {priorityTier.action}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-3xl font-bold text-blue-400">
                              {score}<span className="text-sm text-gray-400">/100</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Score Breakdown */}
                      <div className="bg-[#2d2d30] rounded p-3 mb-4">
                        <h4 className="text-xs font-semibold text-gray-300 mb-2">Score Components:</h4>
                        <div className="space-y-1.5 text-xs">
                          <div className="flex justify-between">
                            <span className="text-gray-400">Severity Impact (40%):</span>
                            <span className="text-orange-400 font-medium">{Math.round(severityScore * 0.4)}/40 pts ({selectedInsightDetail.severity})</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-400">ACV Impact (20%):</span>
                            <span className="text-purple-400 font-medium">{Math.round(acvScore)}/20 pts (${(selectedInsightDetail.metrics.acv_sum / 1000).toFixed(0)}k)</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-400">Effort ROI (20%):</span>
                            <span className="text-blue-400 font-medium">{Math.round(effortScore * 0.2)}/20 pts ({selectedInsightDetail.effort} effort)</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-400">Frequency (10%):</span>
                            <span className="text-green-400 font-medium">{Math.round(freqScore)}/10 pts ({selectedInsightDetail.feedback_count} mentions)</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-400">Trend (10%):</span>
                            <span className={selectedInsightDetail.metrics.trend > 0 ? 'text-green-400' : 'text-gray-400'}>
                              {trendScore}/10 pts ({selectedInsightDetail.metrics.trend > 0 ? '↗ Growing' : '→ Stable'})
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Impact Summary */}
                      <div className="grid grid-cols-2 gap-3 mb-4">
                        <div className="bg-[#2d2d30] p-3 rounded">
                          <div className="text-xs text-gray-400 mb-1">Customer Impact</div>
                          <div className="text-lg font-bold text-gray-200">{customerCount} customers</div>
                          <div className="text-xs text-gray-400 mt-1">
                            {entCount > 0 && <span className="text-purple-400">{entCount} ENT</span>}
                            {mmCount > 0 && <span className="text-blue-400 ml-2">{mmCount} MM</span>}
                            {smbCount > 0 && <span className="text-gray-400 ml-2">{smbCount} SMB</span>}
                          </div>
                        </div>
                        <div className="bg-[#2d2d30] p-3 rounded">
                          <div className="text-xs text-gray-400 mb-1">Activity (30d / 90d)</div>
                          <div className="text-lg font-bold text-gray-200">
                            {selectedInsightDetail.metrics.freq_30d} / {selectedInsightDetail.metrics.freq_90d}
                          </div>
                          <div className="text-xs text-gray-400 mt-1">{selectedInsightDetail.feedback_count} total mentions</div>
                        </div>
                      </div>

                      {/* Actionable Recommendations */}
                      <div className="bg-blue-900/20 border border-blue-500/30 rounded p-3">
                        <h4 className="text-xs font-semibold text-blue-300 mb-2">💡 Recommended Actions:</h4>
                        <ul className="space-y-1 text-xs text-gray-300">
                          {selectedInsightDetail.metrics.acv_sum > 500000 && selectedInsightDetail.effort === 'low' && (
                            <li>• <span className="text-green-400">Quick win:</span> High ACV + Low effort = Fast ROI opportunity</li>
                          )}
                          {entCount >= 2 && (
                            <li>• <span className="text-purple-400">Enterprise focus:</span> {entCount} enterprise customers affected - consider exec review</li>
                          )}
                          {selectedInsightDetail.severity === 'critical' && (
                            <li>• <span className="text-red-400">Urgent:</span> Critical severity - blocking customer success</li>
                          )}
                          {selectedInsightDetail.metrics.trend > 0 && (
                            <li>• <span className="text-orange-400">Trending up:</span> Growing issue - address before it escalates</li>
                          )}
                          {selectedInsightDetail.metrics.trend <= 0 && score >= 60 && (
                            <li>• <span className="text-blue-400">Stable priority:</span> Consistent demand - good candidate for Q1 roadmap</li>
                          )}
                          {selectedInsightDetail.effort === 'high' && score < 70 && (
                            <li>• <span className="text-yellow-400">High effort:</span> Requires significant investment - validate ROI first</li>
                          )}
                        </ul>
                      </div>
                    </div>
                  )
                })()}

                {/* Methodology */}
                <div className="bg-[#1e1e1e] rounded-lg p-4 mb-6 border border-[#3e3e42]">
                  <h3 className="text-sm font-semibold text-gray-200 mb-3 flex items-center gap-2">
                    📋 Scoring Methodology
                  </h3>
                  <div className="space-y-3 text-xs text-gray-400">
                    <div>
                      <span className="font-semibold text-orange-400">Severity:</span> Measures customer & business impact based on:
                      <ul className="ml-4 mt-1 space-y-1">
                        <li>• <span className="text-red-400">Critical:</span> Blocking enterprise deals or affecting key customers</li>
                        <li>• <span className="text-orange-400">High:</span> Significant impact on revenue or customer satisfaction</li>
                        <li>• <span className="text-yellow-400">Medium:</span> Notable but not urgent business impact</li>
                        <li>• <span className="text-gray-400">Low:</span> Minor impact, nice-to-have features</li>
                      </ul>
                    </div>
                    <div>
                      <span className="font-semibold text-blue-400">Effort:</span> Estimated engineering time investment:
                      <ul className="ml-4 mt-1 space-y-1">
                        <li>• <span className="text-green-400">Low:</span> 1-5 days of development</li>
                        <li>• <span className="text-blue-400">Medium:</span> 1-4 weeks of development</li>
                        <li>• <span className="text-purple-400">High:</span> 1+ months of development</li>
                      </ul>
                    </div>
                    <div>
                      <span className="font-semibold text-blue-400">Priority Score:</span> Calculated using a weighted formula:
                      <ul className="ml-4 mt-1 space-y-1">
                        <li>• Severity weight (40%): Impact on customers and business</li>
                        <li>• Effort weight (20%): Inverse of development time</li>
                        <li>• ACV weight (20%): Total contract value of affected customers</li>
                        <li>• Frequency weight (10%): How often this issue appears</li>
                        <li>• Trend weight (10%): Whether mentions are increasing</li>
                      </ul>
                      <p className="mt-2 text-gray-500">Score range: 0-100 (higher = more urgent)</p>
                    </div>
                  </div>
                </div>

                {/* Key Evidence */}
                {selectedInsightDetail.key_quotes && selectedInsightDetail.key_quotes.length > 0 && (
                  <div className="mb-6">
                    <h4 className="text-sm font-semibold text-gray-200 mb-3">🎯 Key Evidence ({selectedInsightDetail.key_quotes.length})</h4>
                    <div className="space-y-3">
                      {selectedInsightDetail.key_quotes.map((feedback) => (
                        <div key={feedback.id} className="bg-blue-900/20 border-l-4 border-blue-500 p-3 rounded">
                          <p className="text-sm text-gray-300 mb-2">&quot;{feedback.text}&quot;</p>
                          <div className="flex flex-wrap gap-2 items-center text-xs">
                            <span className={`px-2 py-1 rounded font-medium ${SOURCE_COLORS[feedback.source] || 'bg-gray-700 text-gray-300'}`}>
                              {SOURCE_ICONS[feedback.source] || '📌'} {feedback.source.toUpperCase()}
                            </span>
                            {feedback.account && (
                              <span className="text-gray-400 font-medium">{feedback.account}</span>
                            )}
                            <span className="text-gray-500">
                              {new Date(feedback.created_at).toLocaleDateString()}
                            </span>
                            <span className="text-blue-400">
                              {Math.round(feedback.confidence)}% confidence
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Supporting Feedback */}
                {selectedInsightDetail.supporting_feedback && selectedInsightDetail.supporting_feedback.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-200 mb-3">📋 Supporting Feedback ({selectedInsightDetail.supporting_feedback.length})</h4>
                    <div className="space-y-3">
                      {selectedInsightDetail.supporting_feedback.slice(0, 5).map((feedback) => (
                        <div key={feedback.id} className="bg-[#2d2d30] border-l-4 border-gray-600 p-3 rounded">
                          <p className="text-sm text-gray-400 mb-2">&quot;{feedback.text}&quot;</p>
                          <div className="flex flex-wrap gap-2 items-center text-xs">
                            <span className={`px-2 py-1 rounded font-medium ${SOURCE_COLORS[feedback.source] || 'bg-gray-700 text-gray-300'}`}>
                              {SOURCE_ICONS[feedback.source] || '📌'} {feedback.source.toUpperCase()}
                            </span>
                            {feedback.account && (
                              <span className="text-gray-500">{feedback.account}</span>
                            )}
                          </div>
                        </div>
                      ))}
                      {selectedInsightDetail.supporting_feedback.length > 5 && (
                        <div className="text-xs text-gray-500 text-center">
                          +{selectedInsightDetail.supporting_feedback.length - 5} more items
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </aside>
      )}

      {/* AI Prototype Modal */}
      {showAIPrototypeModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-[#252526] border border-[#3e3e42] rounded-lg w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#3e3e42]">
              <h2 className="text-lg font-semibold text-gray-100">🚀 Generate AI Prototype</h2>
              <button
                onClick={handleCloseAIPrototypeModal}
                className="p-1 hover:bg-[#3e3e42] rounded text-gray-400 hover:text-gray-200 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {/* Recommended Tool Badge */}
              {recommendedTool && (
                <div className="mb-4">
                  <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-900/30 border border-blue-500/50 rounded-lg">
                    <span className="text-sm font-semibold text-blue-300">
                      ✨ Recommended: {recommendedTool}
                    </span>
                  </div>
                  {toolReason && (
                    <p className="text-sm text-gray-400 mt-2">{toolReason}</p>
                  )}
                </div>
              )}

              {/* Prompt Display */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Generated Prompt
                </label>
                <textarea
                  value={aiPrompt}
                  readOnly
                  className="w-full h-64 bg-[#1e1e1e] text-gray-300 p-4 rounded border border-[#3e3e42] focus:outline-none focus:border-blue-500 font-mono text-sm resize-none"
                  style={{ whiteSpace: 'pre-wrap' }}
                />
              </div>

              {/* Copy Button */}
              <div className="mb-4">
                <button
                  onClick={handleCopyPrompt}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium transition-colors"
                >
                  {copiedPrompt ? '✓ Copied!' : '📋 Copy to Clipboard'}
                </button>
              </div>

              {/* Quick Launch Buttons */}
              <div className="border-t border-[#3e3e42] pt-4">
                <h3 className="text-sm font-medium text-gray-300 mb-3">Quick Launch</h3>
                <div className="flex flex-wrap gap-3">
                  <a
                    href="https://lovable.dev"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded text-sm font-medium transition-colors inline-flex items-center gap-2"
                  >
                    Open in Lovable →
                  </a>
                  <a
                    href="https://bolt.new"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded text-sm font-medium transition-colors inline-flex items-center gap-2"
                  >
                    Try Bolt →
                  </a>
                  <a
                    href="https://v0.dev"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded text-sm font-medium transition-colors inline-flex items-center gap-2"
                  >
                    Try v0 →
                  </a>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-[#3e3e42] flex justify-end">
              <button
                onClick={handleCloseAIPrototypeModal}
                className="px-4 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] rounded text-sm font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  )
}
