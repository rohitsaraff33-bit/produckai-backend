'use client'

import { useEffect, useState, useRef } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ClusteringStatus {
  is_running: boolean
  status: string
  started_at?: string
  completed_at?: string
  themes_created?: number
  insights_created?: number
  error?: string
}

export default function InsightGenerationBanner() {
  const [status, setStatus] = useState<ClusteringStatus | null>(null)
  const [showBanner, setShowBanner] = useState(false)

  const checkStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/cluster/status`)
      const data: ClusteringStatus = await response.json()
      setStatus(data)

      // Show banner if running
      if (data.is_running) {
        setShowBanner(true)
        // Clear the reloaded flag when new job starts
        if (typeof window !== 'undefined') {
          localStorage.removeItem('last_reloaded_completion')
        }
      }

      // Show banner briefly when just completed
      if (data.status === 'completed' && !data.is_running && data.completed_at) {
        setShowBanner(true)
      }
    } catch (error) {
      console.error('Failed to check clustering status:', error)
    }
  }

  useEffect(() => {
    // Check status immediately
    checkStatus()

    // Poll every 5 seconds
    const interval = setInterval(checkStatus, 5000)

    return () => clearInterval(interval)
  }, [])

  // Auto-dismiss completed banner after 10 seconds
  useEffect(() => {
    if (status?.status === 'completed' && !status.is_running) {
      const timer = setTimeout(() => {
        setShowBanner(false)
      }, 10000)

      return () => clearTimeout(timer)
    }
  }, [status])

  // Reload page ONCE when clustering completes (only for new completions)
  useEffect(() => {
    if (
      status?.status === 'completed' &&
      !status.is_running &&
      status.insights_created &&
      status.completed_at &&
      typeof window !== 'undefined'
    ) {
      // Check if we've already reloaded for this completion
      const lastReloaded = localStorage.getItem('last_reloaded_completion')

      if (lastReloaded !== status.completed_at) {
        // Mark this completion as reloaded before actually reloading
        localStorage.setItem('last_reloaded_completion', status.completed_at)

        // Reload insights after a short delay
        setTimeout(() => {
          window.location.reload()
        }, 2000)
      }
    }
  }, [status])

  if (!showBanner || !status) return null

  return (
    <div className="fixed top-0 left-0 right-0 z-50 animate-in slide-in-from-top">
      {status.is_running && (
        <div className="bg-blue-900/90 border-b border-blue-500/30 px-6 py-3">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="flex items-center gap-3">
              <div className="animate-spin h-5 w-5 border-2 border-blue-400 border-t-transparent rounded-full"></div>
              <div>
                <div className="text-sm font-semibold text-blue-100">
                  Generating Insights...
                </div>
                <div className="text-xs text-blue-300">
                  Analyzing feedback and creating themes. This may take a few minutes.
                </div>
              </div>
            </div>
            <button
              onClick={() => setShowBanner(false)}
              className="text-blue-300 hover:text-blue-100 text-xl"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {status.status === 'completed' && !status.is_running && (
        <div className="bg-green-900/90 border-b border-green-500/30 px-6 py-3">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="flex items-center gap-3">
              <span className="text-2xl">✅</span>
              <div>
                <div className="text-sm font-semibold text-green-100">
                  Insights Generated Successfully!
                </div>
                <div className="text-xs text-green-300">
                  Created {status.themes_created || 0} themes and {status.insights_created || 0} insights.
                  Page will refresh automatically...
                </div>
              </div>
            </div>
            <button
              onClick={() => setShowBanner(false)}
              className="text-green-300 hover:text-green-100 text-xl"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {status.status === 'failed' && !status.is_running && (
        <div className="bg-red-900/90 border-b border-red-500/30 px-6 py-3">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="flex items-center gap-3">
              <span className="text-2xl">❌</span>
              <div>
                <div className="text-sm font-semibold text-red-100">
                  Insight Generation Failed
                </div>
                <div className="text-xs text-red-300">
                  {status.error || 'An error occurred during clustering'}
                </div>
              </div>
            </div>
            <button
              onClick={() => setShowBanner(false)}
              className="text-red-300 hover:text-red-100 text-xl"
            >
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
