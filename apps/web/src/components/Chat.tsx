'use client'

import { useState, useRef, useEffect } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ChatProps {
  selectedInsightId?: string | null
  onClose: () => void
}

const SUGGESTED_QUESTIONS = [
  {
    icon: '🎯',
    text: 'What should I focus on for next quarter?',
  },
  {
    icon: '📊',
    text: 'What are my top customer complaints?',
  },
  {
    icon: '⚡',
    text: 'Show me quick wins',
  },
  {
    icon: '🏢',
    text: 'What is blocking enterprise deals?',
  },
]

export default function Chat({ selectedInsightId, onClose }: ChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const sendMessage = async (messageText?: string) => {
    const text = messageText || input.trim()
    if (!text) return

    // Add user message
    const userMessage: ChatMessage = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          selected_insight_id: selectedInsightId,
          conversation_history: messages.slice(-4), // Last 4 messages for context
        }),
      })

      if (!response.ok) throw new Error('Failed to send message')

      const data = await response.json()
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.response,
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error('Failed to send message:', error)
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <aside className="w-96 bg-[#252526] border-l border-[#3e3e42] flex flex-col">
      {/* Chat Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-[#3e3e42]">
        <h3 className="font-semibold text-sm">AI Assistant</h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-[#3e3e42] rounded text-gray-400 hover:text-gray-200"
        >
          ✕
        </button>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="space-y-4">
            {/* Welcome Message */}
            <div className="bg-[#3e3e42] rounded-lg p-4">
              <p className="text-sm text-gray-300 mb-3">
                👋 Hi! I'm your PM copilot. I can help you:
              </p>
              <div className="space-y-2 text-sm">
                {SUGGESTED_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => sendMessage(q.text)}
                    className="w-full text-left px-3 py-2 bg-[#2d2d30] hover:bg-[#3e3e42] rounded transition-colors text-gray-200"
                  >
                    {q.icon} {q.text}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message, idx) => (
              <div
                key={idx}
                className={`${
                  message.role === 'user'
                    ? 'ml-8 bg-blue-600 text-white'
                    : 'mr-8 bg-[#3e3e42] text-gray-200'
                } rounded-lg p-3 text-sm whitespace-pre-wrap`}
              >
                {message.content}
              </div>
            ))}
            {loading && (
              <div className="mr-8 bg-[#3e3e42] rounded-lg p-3 text-sm text-gray-400">
                <div className="flex items-center gap-2">
                  <div className="animate-pulse">●</div>
                  <div className="animate-pulse delay-75">●</div>
                  <div className="animate-pulse delay-150">●</div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Chat Input */}
      <div className="p-4 border-t border-[#3e3e42]">
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask anything..."
            disabled={loading}
            className="w-full px-4 py-2.5 bg-[#3e3e42] border border-[#5e5e62] rounded-lg focus:outline-none focus:border-blue-500 text-sm disabled:opacity-50"
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-blue-400 hover:text-blue-300 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            ↵
          </button>
        </div>
        {selectedInsightId && (
          <div className="mt-2 text-xs text-gray-500">
            💡 Context: Selected insight active
          </div>
        )}
      </div>
    </aside>
  )
}
