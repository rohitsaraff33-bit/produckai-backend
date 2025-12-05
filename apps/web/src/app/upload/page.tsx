'use client'

import { useState, useRef, DragEvent } from 'react'
import { useRouter } from 'next/navigation'
import Layout from '../../components/Layout'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface UploadResult {
  filename: string
  success: boolean
  feedback_count?: number
  error?: string
}

export default function UploadPage() {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadResults, setUploadResults] = useState<UploadResult[]>([])
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const router = useRouter()

  const handleDrag = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const droppedFiles = Array.from(e.dataTransfer.files)
    const validFiles = droppedFiles.filter(file => {
      const extension = file.name.toLowerCase().split('.').pop()
      return ['csv', 'pdf', 'doc', 'docx', 'txt'].includes(extension || '')
    })

    if (validFiles.length > 0) {
      setFiles(prev => [...prev, ...validFiles])
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files)
      setFiles(prev => [...prev, ...selectedFiles])
    }
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (files.length === 0) return

    setUploading(true)
    setUploadResults([])

    const formData = new FormData()
    // Append all files with the same field name 'files'
    files.forEach(file => {
      formData.append('files', file)
    })

    try {
      const response = await fetch(`${API_URL}/upload/upload-feedback`, {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (response.ok) {
        // API returns: { total_files, successful_files, failed_files, total_feedback_items, errors, message }
        const results: UploadResult[] = files.map(file => {
          const error = data.errors?.find((e: any) => e.filename === file.name)
          if (error) {
            return {
              filename: file.name,
              success: false,
              error: error.error || 'Upload failed',
            }
          }
          return {
            filename: file.name,
            success: true,
            feedback_count: Math.floor(data.total_feedback_items / data.successful_files) || 0,
          }
        })
        setUploadResults(results)
      } else {
        // If entire request fails, mark all files as failed
        const results: UploadResult[] = files.map(file => ({
          filename: file.name,
          success: false,
          error: data.detail || data.message || 'Upload failed',
        }))
        setUploadResults(results)
      }
    } catch (error) {
      // Network error - mark all files as failed
      const results: UploadResult[] = files.map(file => ({
        filename: file.name,
        success: false,
        error: 'Network error',
      }))
      setUploadResults(results)
    }

    setUploading(false)
    setFiles([])
  }

  const totalIngested = uploadResults
    .filter(r => r.success)
    .reduce((sum, r) => sum + (r.feedback_count || 0), 0)

  const handleTriggerClustering = () => {
    router.push('/')
    // The clustering can be triggered from the main page or through the API
    // Optionally, we could add a button on the main page or automatically trigger it
  }

  const handleDownloadTemplate = () => {
    // Create CSV template content
    const csvContent = `Company Name,ACV,Company Contact,Feedback
"Small Business Inc",45000,"contact@smallbiz.com","The mobile app crashes when exporting large datasets to CSV. This is blocking our quarterly reporting workflow."
"Mid Market Corp",150000,"john.doe@midmarket.com","We urgently need SSO/SAML integration for enterprise deployment. Our security team won't approve without it."
"Enterprise Co",500000,"sarah.smith@enterprise.com","Dark mode would be a great addition for users who work late nights. Many of our team members have requested this."`

    // Create blob and download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', 'feedback_template.csv')
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-6 py-6">
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-2xl font-bold text-gray-100">Upload Feedback</h1>
            <button
              onClick={handleDownloadTemplate}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-sm font-medium transition-colors"
            >
              <span>⬇</span>
              Download CSV Template
            </button>
          </div>
          <p className="text-sm text-gray-400">
            Upload customer feedback from various file formats. Supported formats: CSV, PDF, DOC, DOCX, TXT
          </p>
        </div>

        {/* Upload Area */}
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragActive
              ? 'border-blue-500 bg-blue-900/10'
              : 'border-[#3e3e42] hover:border-[#5e5e62]'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="flex flex-col items-center gap-4">
            <div className="text-5xl">📤</div>
            <div>
              <h3 className="text-lg font-semibold text-gray-200 mb-1">
                Drop files here or click to browse
              </h3>
              <p className="text-sm text-gray-400">
                Supports: .csv, .pdf, .doc, .docx, .txt
              </p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".csv,.pdf,.doc,.docx,.txt"
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium transition-colors"
            >
              Select Files
            </button>
          </div>
        </div>

        {/* Selected Files */}
        {files.length > 0 && (
          <div className="mt-6 bg-[#252526] border border-[#3e3e42] rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">
              Selected Files ({files.length})
            </h3>
            <div className="space-y-2">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between bg-[#1e1e1e] p-3 rounded"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">📄</span>
                    <div>
                      <div className="text-sm font-medium text-gray-200">{file.name}</div>
                      <div className="text-xs text-gray-400">
                        {(file.size / 1024).toFixed(2)} KB
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="p-2 hover:bg-[#3e3e42] rounded text-gray-400 hover:text-gray-200"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
            <div className="mt-4 flex gap-2">
              <button
                onClick={handleUpload}
                disabled={uploading}
                className={`flex-1 px-6 py-2 rounded text-sm font-medium transition-colors ${
                  uploading
                    ? 'bg-gray-600 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {uploading ? 'Uploading...' : 'Upload All Files'}
              </button>
              <button
                onClick={() => setFiles([])}
                className="px-6 py-2 bg-[#3e3e42] hover:bg-[#4e4e52] rounded text-sm font-medium transition-colors"
              >
                Clear All
              </button>
            </div>
          </div>
        )}

        {/* Upload Results */}
        {uploadResults.length > 0 && (
          <div className="mt-6 bg-[#252526] border border-[#3e3e42] rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">Upload Results</h3>

            {/* Summary */}
            {totalIngested > 0 && (
              <div className="mb-4 p-4 bg-green-900/20 border border-green-500/30 rounded">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">✅</span>
                  <span className="text-lg font-semibold text-green-400">
                    Successfully ingested {totalIngested} feedback items
                  </span>
                </div>
                <button
                  onClick={handleTriggerClustering}
                  className="mt-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-sm font-medium transition-colors"
                >
                  Go to Insights Dashboard
                </button>
              </div>
            )}

            {/* Individual Results */}
            <div className="space-y-2">
              {uploadResults.map((result, index) => (
                <div
                  key={index}
                  className={`flex items-center justify-between p-3 rounded ${
                    result.success
                      ? 'bg-green-900/20 border border-green-500/30'
                      : 'bg-red-900/20 border border-red-500/30'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{result.success ? '✅' : '❌'}</span>
                    <div>
                      <div className="text-sm font-medium text-gray-200">{result.filename}</div>
                      {result.success ? (
                        <div className="text-xs text-green-400">
                          {result.feedback_count} feedback items ingested
                        </div>
                      ) : (
                        <div className="text-xs text-red-400">{result.error}</div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Help Text */}
        <div className="mt-6 bg-blue-900/10 border border-blue-500/30 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-blue-400 mb-2">📋 File Format Guidelines</h3>
          <ul className="text-xs text-gray-400 space-y-2">
            <li>
              <strong className="text-gray-300">CSV:</strong> Use the template above with columns:
              <div className="ml-4 mt-1 text-gray-500">
                • <span className="text-gray-300">Company Name</span> - Customer company name<br/>
                • <span className="text-gray-300">ACV</span> - Annual Contract Value (number)<br/>
                <span className="ml-2 text-xs text-gray-600">
                  Segmentation: SMB (≤$50k), MM ($50k-$200k), ENT (&gt;$200k)
                </span><br/>
                • <span className="text-gray-300">Company Contact</span> - Contact email (optional)<br/>
                • <span className="text-gray-300">Feedback</span> - Customer feedback text (required)
              </div>
            </li>
            <li>
              <strong className="text-gray-300">PDF:</strong> Text will be extracted from the document
            </li>
            <li>
              <strong className="text-gray-300">DOC/DOCX:</strong> Text will be extracted from Word documents
            </li>
            <li>
              <strong className="text-gray-300">TXT:</strong> Plain text files will be processed line by line
            </li>
          </ul>
        </div>
      </div>
    </Layout>
  )
}
