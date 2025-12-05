'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import Layout from '../../components/Layout'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Integration {
  provider: string
  connected: boolean
  account_email?: string
  scopes?: string
  expires_at?: string
}

const PROVIDER_INFO = {
  zoom: {
    name: 'Zoom',
    icon: '🎥',
    description: 'Connect Zoom to automatically import meeting transcripts and recordings',
    color: 'blue',
  },
  google: {
    name: 'Google Drive',
    icon: '📄',
    description: 'Import product specs and documents from Google Drive',
    color: 'green',
  },
  slack: {
    name: 'Slack',
    icon: '💬',
    description: 'Import feedback from Slack channels',
    color: 'purple',
  },
}

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState<string | null>(null)
  const searchParams = useSearchParams()

  useEffect(() => {
    fetchIntegrations()

    // Check for OAuth callback status
    const status = searchParams.get('status')
    const provider = searchParams.get('provider')
    if (status === 'success' && provider) {
      // Show success notification
      setTimeout(() => {
        fetchIntegrations() // Refresh integrations list
      }, 1000)
    }
  }, [searchParams])

  const fetchIntegrations = async () => {
    try {
      const response = await fetch(`${API_URL}/integrations`)
      const data = await response.json()
      setIntegrations(data)
    } catch (error) {
      console.error('Failed to fetch integrations:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleConnect = async (provider: string) => {
    try {
      const response = await fetch(`${API_URL}/auth/${provider}/start`)
      const data = await response.json()

      if (data.authorization_url) {
        // Redirect to OAuth authorization page
        window.location.href = data.authorization_url
      }
    } catch (error) {
      console.error(`Failed to start ${provider} OAuth:`, error)
      alert(`Failed to connect to ${provider}. Please try again.`)
    }
  }

  const handleDisconnect = async (provider: string) => {
    if (!confirm(`Are you sure you want to disconnect ${provider}?`)) {
      return
    }

    try {
      await fetch(`${API_URL}/integrations/${provider}/disconnect`, {
        method: 'DELETE',
      })
      fetchIntegrations()
    } catch (error) {
      console.error(`Failed to disconnect ${provider}:`, error)
      alert(`Failed to disconnect ${provider}. Please try again.`)
    }
  }

  const handleSync = async (provider: string) => {
    let url = `${API_URL}/integrations/${provider}/sync`

    // For Google Drive, prompt for folder IDs
    if (provider === 'google') {
      const folderIds = prompt(
        'Enter Google Drive folder IDs (comma-separated):\n\n' +
        'Example: 1a2b3c4d5e6f,7g8h9i0j1k2l\n\n' +
        'To find a folder ID:\n' +
        '1. Open the folder in Google Drive\n' +
        '2. Copy the ID from the URL after /folders/'
      )

      if (!folderIds || !folderIds.trim()) {
        alert('Folder IDs are required for Google Drive sync')
        return
      }

      url += `?folder_ids=${encodeURIComponent(folderIds)}`
    }

    setSyncing(provider)
    try {
      const response = await fetch(url, {
        method: 'POST',
      })
      const data = await response.json()

      if (data.stats) {
        if (provider === 'zoom') {
          alert(
            `Sync completed!\n\n` +
            `Recordings: ${data.stats.recordings_found}\n` +
            `Transcripts: ${data.stats.transcripts_found}\n` +
            `Created: ${data.stats.feedback_created}\n` +
            `Updated: ${data.stats.feedback_updated}`
          )
        } else if (provider === 'google') {
          alert(
            `Sync completed!\n\n` +
            `Files found: ${data.stats.files_found}\n` +
            `Documents processed: ${data.stats.documents_processed}\n` +
            `Created: ${data.stats.feedback_created}\n` +
            `Updated: ${data.stats.feedback_updated}`
          )
        }
      }
    } catch (error) {
      console.error(`Failed to sync ${provider}:`, error)
      alert(`Failed to sync ${provider}. Please try again.`)
    } finally {
      setSyncing(null)
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-full">
          <div className="text-lg">Loading integrations...</div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-100 mb-2">Integrations</h1>
          <p className="text-gray-400">
            Connect your data sources to automatically import feedback, transcripts, and documents.
          </p>
        </div>

        <div className="space-y-4">
          {integrations.map((integration) => {
            const info = PROVIDER_INFO[integration.provider as keyof typeof PROVIDER_INFO]
            if (!info) return null

            const isConnected = integration.connected
            const colorClasses = {
              blue: 'border-blue-500/30 bg-blue-900/10',
              green: 'border-green-500/30 bg-green-900/10',
              purple: 'border-purple-500/30 bg-purple-900/10',
            }
            const buttonClasses = {
              blue: 'bg-blue-600 hover:bg-blue-700',
              green: 'bg-green-600 hover:bg-green-700',
              purple: 'bg-purple-600 hover:bg-purple-700',
            }

            return (
              <div
                key={integration.provider}
                className={`bg-[#252526] border-2 rounded-lg p-6 ${
                  isConnected ? colorClasses[info.color as keyof typeof colorClasses] : 'border-[#3e3e42]'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    <div className="text-4xl">{info.icon}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-100">{info.name}</h3>
                        {isConnected && (
                          <span className="flex items-center gap-1.5 px-2 py-1 bg-green-600/20 border border-green-500/30 rounded text-xs font-medium text-green-400">
                            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                            Connected
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-400 mb-3">{info.description}</p>

                      {isConnected && (
                        <div className="space-y-1 text-xs text-gray-400">
                          {integration.account_email && (
                            <div>
                              <span className="font-medium text-gray-300">Account:</span> {integration.account_email}
                            </div>
                          )}
                          {integration.expires_at && (
                            <div>
                              <span className="font-medium text-gray-300">Expires:</span>{' '}
                              {new Date(integration.expires_at).toLocaleDateString()}
                            </div>
                          )}
                          {integration.scopes && (
                            <div>
                              <span className="font-medium text-gray-300">Scopes:</span> {integration.scopes}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-2">
                    {isConnected ? (
                      <>
                        {(integration.provider === 'zoom' || integration.provider === 'google') && (
                          <button
                            onClick={() => handleSync(integration.provider)}
                            disabled={syncing === integration.provider}
                            className={`px-4 py-2 ${
                              buttonClasses[info.color as keyof typeof buttonClasses]
                            } text-white rounded text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
                          >
                            {syncing === integration.provider ? '⏳ Syncing...' : '🔄 Sync Now'}
                          </button>
                        )}
                        <button
                          onClick={() => handleDisconnect(integration.provider)}
                          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-medium transition-colors"
                        >
                          Disconnect
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => handleConnect(integration.provider)}
                        className={`px-4 py-2 ${
                          buttonClasses[info.color as keyof typeof buttonClasses]
                        } text-white rounded text-sm font-medium transition-colors`}
                      >
                        Connect
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        <div className="mt-8 p-4 bg-[#252526] border border-[#3e3e42] rounded-lg">
          <h3 className="text-sm font-semibold text-gray-200 mb-2 flex items-center gap-2">
            ℹ️ About Integrations
          </h3>
          <div className="text-xs text-gray-400 space-y-1">
            <p>• OAuth connections are stored securely with AES-256 encryption</p>
            <p>• Tokens are automatically refreshed when needed</p>
            <p>• Data is synced periodically or can be triggered manually</p>
            <p>• You can disconnect at any time to revoke access</p>
          </div>
        </div>
      </div>
    </Layout>
  )
}
