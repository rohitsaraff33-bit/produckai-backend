'use client'

import { ReactNode, useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import Chat from './Chat'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface LayoutProps {
  children: ReactNode
  showChat?: boolean
  onChatToggle?: () => void
  selectedInsightId?: string | null
}

interface Customer {
  name: string
  insight_count: number
  feedback_count: number
}

interface FilterCounts {
  enterprise_blockers: number
  high_priority: number
  trending: number
}

export default function Layout({ children, showChat = false, onChatToggle, selectedInsightId }: LayoutProps) {
  const [leftPanelCollapsed, setLeftPanelCollapsed] = useState(false)
  const [rightPanelOpen, setRightPanelOpen] = useState(showChat)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [filterCounts, setFilterCounts] = useState<FilterCounts>({ enterprise_blockers: 0, high_priority: 0, trending: 0 })
  const router = useRouter()
  const searchParams = useSearchParams()
  const selectedCustomer = searchParams.get('customer')
  const selectedFilter = searchParams.get('filter')

  // Fetch customers
  useEffect(() => {
    const fetchCustomers = async () => {
      try {
        const response = await fetch(`${API_URL}/customers`)
        const data = await response.json()
        setCustomers(data.customers || [])
      } catch (error) {
        console.error('Failed to fetch customers:', error)
      }
    }
    fetchCustomers()
  }, [])

  // Fetch filter counts
  useEffect(() => {
    const fetchFilterCounts = async () => {
      try {
        const response = await fetch(`${API_URL}/themes/filter-counts`)
        const data = await response.json()
        setFilterCounts(data)
      } catch (error) {
        console.error('Failed to fetch filter counts:', error)
      }
    }
    fetchFilterCounts()
  }, [])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // ⌘B or Ctrl+B: Toggle left panel
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault()
        setLeftPanelCollapsed(!leftPanelCollapsed)
      }
      // ⌘K or Ctrl+K: Toggle command palette / chat
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setRightPanelOpen(!rightPanelOpen)
        onChatToggle?.()
      }
      // Escape: Close right panel
      if (e.key === 'Escape' && rightPanelOpen) {
        setRightPanelOpen(false)
        onChatToggle?.()
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [leftPanelCollapsed, rightPanelOpen, onChatToggle])

  return (
    <div className="flex h-screen bg-[#1e1e1e] text-gray-100">
      {/* Left Sidebar - Data Sources */}
      <aside
        className={`${
          leftPanelCollapsed ? 'w-12' : 'w-64'
        } bg-[#252526] border-r border-[#3e3e42] transition-all duration-200 flex flex-col`}
      >
        {/* Header */}
        <div className="h-14 flex items-center justify-between px-4 border-b border-[#3e3e42]">
          {!leftPanelCollapsed && (
            <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <img
                src="/logo.svg"
                alt="ProduckAI"
                className="h-12 w-auto"
              />
            </Link>
          )}
          <button
            onClick={() => setLeftPanelCollapsed(!leftPanelCollapsed)}
            className="p-1 hover:bg-[#3e3e42] rounded text-gray-400 hover:text-gray-200"
            title={leftPanelCollapsed ? 'Expand sidebar (⌘B)' : 'Collapse sidebar (⌘B)'}
          >
            {leftPanelCollapsed ? '→' : '←'}
          </button>
        </div>

        {/* Data Sources */}
        {!leftPanelCollapsed && (
          <div className="flex-1 overflow-y-auto p-4">
            <div className="mb-6">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                Data Sources
              </h3>
              <div className="space-y-1">
                <Link
                  href="/upload"
                  className="flex items-center gap-2 px-3 py-2 rounded hover:bg-[#3e3e42] cursor-pointer transition-colors"
                >
                  <span className="text-base">📤</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-200">Upload Feedback</div>
                    <div className="text-xs text-gray-400 truncate">Import files</div>
                  </div>
                </Link>
                <DataSourceItem icon="💬" name="Slack" count="23 channels" connected sourceId="slack" />
                <DataSourceItem icon="🎫" name="Jira" count="156 issues" connected sourceId="jira" />
                <DataSourceItem icon="🎥" name="Zoom" count="12 transcripts" connected sourceId="zoom" />
                <DataSourceItem icon="📄" name="GDrive" count="8 specs" connected sourceId="gdrive" />
                <DataSourceItem icon="📊" name="Linear" count="Not connected" connected={false} />
              </div>
            </div>

            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Quick Filters
                </h3>
                {selectedFilter && (
                  <button
                    onClick={() => router.push('/')}
                    className="text-xs text-blue-400 hover:text-blue-300"
                    title="Clear filter"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="space-y-1">
                <FilterItem
                  icon="⭐"
                  name="Enterprise Blockers"
                  count={filterCounts.enterprise_blockers}
                  filterId="enterprise_blockers"
                  isActive={selectedFilter === 'enterprise_blockers'}
                />
                <FilterItem
                  icon="🔥"
                  name="High Priority"
                  count={filterCounts.high_priority}
                  filterId="high_priority"
                  isActive={selectedFilter === 'high_priority'}
                />
                <FilterItem
                  icon="📈"
                  name="Trending"
                  count={filterCounts.trending}
                  filterId="trending"
                  isActive={selectedFilter === 'trending'}
                />
              </div>
            </div>

            <div className="mb-6">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                Intelligence
              </h3>
              <div className="space-y-1">
                <Link
                  href="/competitive"
                  className="flex items-center gap-2 px-3 py-2 rounded hover:bg-[#3e3e42] cursor-pointer transition-colors"
                >
                  <span className="text-base">⚔️</span>
                  <span className="flex-1 text-sm text-gray-200">Competitive Intel</span>
                </Link>
              </div>
            </div>

            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Customers
                </h3>
                {selectedCustomer && (
                  <button
                    onClick={() => router.push('/')}
                    className="text-xs text-blue-400 hover:text-blue-300"
                    title="Clear customer filter"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {customers.length === 0 ? (
                  <div className="text-xs text-gray-500 px-3 py-2">Loading...</div>
                ) : (
                  customers.map((customer) => (
                    <button
                      key={customer.name}
                      onClick={() => router.push(`/?customer=${encodeURIComponent(customer.name)}`)}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded hover:bg-[#3e3e42] cursor-pointer transition-colors text-left ${
                        selectedCustomer === customer.name ? 'bg-[#3e3e42] border-l-2 border-blue-500' : ''
                      }`}
                    >
                      <span className="text-base">👤</span>
                      <span className="flex-1 text-sm text-gray-200 truncate">{customer.name}</span>
                      <span className="text-xs text-gray-400 bg-[#3e3e42] px-1.5 py-0.5 rounded">
                        {customer.insight_count}
                      </span>
                    </button>
                  ))
                )}
              </div>
            </div>

            <Link href="/integrations" className="block w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium transition-colors text-center">
              + Add Integration
            </Link>
          </div>
        )}

        {leftPanelCollapsed && (
          <div className="flex-1 p-2">
            <div className="space-y-2 text-center">
              <Link href="/upload" className="block p-2 hover:bg-[#3e3e42] rounded cursor-pointer" title="Upload Feedback">📤</Link>
              <Link href="/sources/slack" className="block p-2 hover:bg-[#3e3e42] rounded cursor-pointer" title="Slack">💬</Link>
              <Link href="/sources/jira" className="block p-2 hover:bg-[#3e3e42] rounded cursor-pointer" title="Jira">🎫</Link>
              <Link href="/sources/zoom" className="block p-2 hover:bg-[#3e3e42] rounded cursor-pointer" title="Zoom">🎥</Link>
              <Link href="/sources/gdrive" className="block p-2 hover:bg-[#3e3e42] rounded cursor-pointer" title="GDrive">📄</Link>
            </div>
          </div>
        )}

        {/* Keyboard Shortcuts Help */}
        {!leftPanelCollapsed && (
          <div className="p-4 border-t border-[#3e3e42] text-xs text-gray-400">
            <div className="space-y-1">
              <div className="flex justify-between">
                <span>Toggle sidebar</span>
                <kbd className="px-1.5 py-0.5 bg-[#3e3e42] rounded">⌘B</kbd>
              </div>
              <div className="flex justify-between">
                <span>Command palette</span>
                <kbd className="px-1.5 py-0.5 bg-[#3e3e42] rounded">⌘K</kbd>
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-14 bg-[#252526] border-b border-[#3e3e42] flex items-center justify-between px-6">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold">Product Insights</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setRightPanelOpen(!rightPanelOpen)
                onChatToggle?.()
              }}
              className={`px-3 py-1.5 ${
                rightPanelOpen ? 'bg-blue-600' : 'bg-[#3e3e42] hover:bg-[#4e4e52]'
              } rounded text-xs font-medium transition-colors flex items-center gap-1.5`}
            >
              💬 AI Assistant
              <kbd className="px-1.5 py-0.5 bg-black/20 rounded text-xs">⌘K</kbd>
            </button>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-auto bg-[#1e1e1e]">
          {children}
        </div>
      </main>

      {/* Right Panel - AI Chat Assistant */}
      {rightPanelOpen && (
        <Chat
          selectedInsightId={selectedInsightId}
          onClose={() => {
            setRightPanelOpen(false)
            onChatToggle?.()
          }}
        />
      )}
    </div>
  )
}

// Helper Components
function DataSourceItem({ icon, name, count, connected, sourceId }: { icon: string; name: string; count: string; connected: boolean; sourceId?: string }) {
  const content = (
    <>
      <span className="text-base">{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-gray-200">{name}</div>
        <div className="text-xs text-gray-400 truncate">{count}</div>
      </div>
      {connected && <span className="w-2 h-2 bg-green-500 rounded-full"></span>}
    </>
  )

  if (connected && sourceId) {
    return (
      <Link href={`/sources/${sourceId}`} className={`flex items-center gap-2 px-3 py-2 rounded cursor-pointer transition-colors hover:bg-[#3e3e42]`}>
        {content}
      </Link>
    )
  }

  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded transition-colors ${
      connected ? 'hover:bg-[#3e3e42] cursor-pointer' : 'opacity-50'
    }`}>
      {content}
    </div>
  )
}

function FilterItem({ icon, name, count, filterId, isActive }: { icon: string; name: string; count: number; filterId: string; isActive: boolean }) {
  const router = useRouter()

  return (
    <button
      onClick={() => router.push(`/?filter=${filterId}`)}
      className={`w-full flex items-center gap-2 px-3 py-2 rounded hover:bg-[#3e3e42] cursor-pointer transition-colors text-left ${
        isActive ? 'bg-[#3e3e42] border-l-2 border-blue-500' : ''
      }`}
    >
      <span className="text-base">{icon}</span>
      <span className="flex-1 text-sm text-gray-200">{name}</span>
      <span className="text-xs text-gray-400 bg-[#3e3e42] px-1.5 py-0.5 rounded">{count}</span>
    </button>
  )
}
