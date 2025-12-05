# ProduckAI Backend API Endpoints

**Version:** Current (as of backend analysis)
**Base URL:** `http://localhost:8000`
**Protocol:** HTTP/REST
**Authentication:** OAuth 2.0 (Google, Zoom)

---

## Table of Contents

1. [Health](#health)
2. [Themes & Insights](#themes--insights)
3. [Clustering](#clustering)
4. [Feedback](#feedback)
5. [Auth](#auth)
6. [Upload](#upload)
7. [Ingest](#ingest)
8. [Customers](#customers)
9. [JIRA VOC Scoring](#jira-voc-scoring)
10. [Integrations](#integrations)
11. [Competitive Intelligence](#competitive-intelligence)
12. [Admin](#admin)
13. [Search](#search)
14. [Chat](#chat)
15. [Artifacts (Tickets)](#artifacts-tickets)

---

## Health

### GET /healthz

Health check endpoint with database connectivity test.

**Response:**
```json
{
  "status": "ok",
  "database": "connected"
}
```

**Error Response:**
```json
{
  "status": "error",
  "database": "disconnected",
  "error": "error message"
}
```

---

## Themes & Insights

### GET /themes

List insights with sorting, filtering, and pagination.

**Query Parameters:**
- `sort_by` (str): `priority` | `score` | `trend` | `created_at` (default: `priority`)
- `filter` (str, optional): `enterprise_blockers` | `high_priority` | `trending`
- `limit` (int): Max results, ≤100 (default: 20)
- `offset` (int): Pagination offset (default: 0)
- `priority_min` (int, optional): Minimum priority score 0-100
- `priority_max` (int, optional): Maximum priority score 0-100
- `severity` (list[str], optional): Filter by severity (critical, high, medium, low)
- `segments` (list[str], optional): Filter by customer segments (ENT, MM, SMB)
- `effort` (list[str], optional): Filter by effort (low, medium, high)

**Response:**
```json
[
  {
    "id": "uuid",
    "title": "API Rate Limiting Issues",
    "description": "Customers experiencing rate limit errors",
    "impact": "Reduced API reliability",
    "recommendation": "Implement dynamic rate limiting",
    "severity": "high",
    "effort": "medium",
    "priority_score": 85,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00",
    "metrics": {
      "freq_30d": 15,
      "freq_90d": 42,
      "acv_sum": 500000,
      "sentiment": 0.3,
      "trend": 2.5,
      "score": 87.5
    },
    "feedback_count": 23,
    "customers": [
      {
        "id": "uuid",
        "name": "Acme Corp",
        "segment": "ENT",
        "acv": 250000
      }
    ],
    "total_acv": 500000
  }
]
```

### GET /themes/filter-counts

Get counts for quick filter categories.

**Response:**
```json
{
  "enterprise_blockers": 5,
  "high_priority": 12,
  "trending": 8
}
```

### GET /themes/{insight_id}

Get detailed insight with supporting feedback.

**Path Parameters:**
- `insight_id` (UUID): Insight identifier

**Response:**
```json
{
  "id": "uuid",
  "title": "API Rate Limiting Issues",
  "description": "...",
  "impact": "...",
  "recommendation": "...",
  "severity": "high",
  "effort": "medium",
  "priority_score": 85,
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:30:00",
  "metrics": {...},
  "feedback_count": 23,
  "customers": [...],
  "total_acv": 500000,
  "key_quotes": [
    {
      "id": "uuid",
      "text": "We're hitting rate limits constantly",
      "source": "slack",
      "source_id": "msg_123",
      "account": "Acme Corp",
      "created_at": "2025-01-10T14:22:00",
      "confidence": 0.95,
      "meta": {},
      "doc_url": null,
      "speaker": "John Doe",
      "started_at": null,
      "ended_at": null
    }
  ],
  "supporting_feedback": [...]
}
```

### GET /themes/{insight_id}/generate-prd

Generate a comprehensive PRD (Product Requirements Document) for an insight.

**Path Parameters:**
- `insight_id` (UUID): Insight identifier

**Response:**
```json
{
  "prd_markdown": "# API Rate Limiting Enhancement\n\n*Generated: Jan 15, 2025* | *Priority: 85/100* | *Severity: HIGH*\n\n**TL;DR**: 23 customers ($500k ACV) reported 15× in 30d. 2 ENT ($300k), 3 MM ($150k), 1 SMB ($50k).\n\n---\n\n## Problem & Goal\n\nCustomers experiencing rate limit errors...",
  "insight_id": "uuid"
}
```

### GET /themes/{insight_id}/generate-ai-prompt

Generate structured AI prototype prompt from insight data.

**Path Parameters:**
- `insight_id` (UUID): Insight identifier

**Query Parameters:**
- `prototype_type` (str): `ui_component` | `feature_flow` | `mvp` | `technical_poc` (default: `mvp`)

**Response:**
```json
{
  "prompt": "# Build: API Rate Limiting Enhancement\n\n## Context\nCreate a functional MVP based on validated customer feedback...",
  "recommended_tool": "Lovable",
  "recommendation_reason": "High-value feature for Enterprise accounts requires production-quality MVP",
  "insight_id": "uuid",
  "metadata": {
    "total_customers": 23,
    "total_acv": "$500k",
    "severity": "high",
    "effort": "medium",
    "has_enterprise_customers": true,
    "integrations": []
  }
}
```

---

## Clustering

### POST /cluster/run

Trigger clustering pipeline as a background task.

**Response:**
```json
{
  "status": "accepted",
  "message": "Clustering task started in background",
  "task_id": null
}
```

**Already Running Response:**
```json
{
  "status": "already_running",
  "message": "Clustering task is already running",
  "task_id": null
}
```

### GET /cluster/status

Get current clustering pipeline status.

**Response:**
```json
{
  "is_running": false,
  "status": "completed",
  "started_at": "2025-01-15T10:00:00",
  "completed_at": "2025-01-15T10:02:30",
  "themes_created": 15,
  "insights_created": 42,
  "error": null
}
```

---

## Feedback

### GET /feedback

List feedback items with optional source filtering.

**Query Parameters:**
- `source` (str, optional): Filter by source (slack, jira, zoom_transcript, gdoc, etc.)
- `limit` (int): Max items (default: 100)
- `offset` (int): Pagination offset (default: 0)

**Response:**
```json
[
  {
    "id": "uuid",
    "source": "slack",
    "source_id": "msg_123",
    "text": "We're hitting rate limits constantly on the API",
    "account": "Acme Corp",
    "created_at": "2025-01-10T14:22:00",
    "meta": {
      "channel": "#customer-feedback",
      "user": "john.doe"
    }
  }
]
```

### GET /feedback/documents

List documents grouped from feedback chunks (for sources like Google Drive).

**Query Parameters:**
- `source` (str, optional): Filter by source (gdoc, zoom_transcript, etc.)

**Response:**
```json
[
  {
    "document_id": "doc_123",
    "title": "Q4 Customer Call - Acme Corp",
    "url": "https://docs.google.com/document/d/...",
    "account": "Acme Corp",
    "created_at": "2025-01-10T09:00:00",
    "modified_at": "2025-01-10T10:30:00",
    "chunk_count": 12,
    "summary": "Customer mentioned rate limiting issues ... API performance concerns ... [+7 more statements]",
    "owner": "pm@company.com"
  }
]
```

---

## Auth

### GET /auth/google/start

Start Google OAuth flow.

**Response:**
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random_state_token"
}
```

### GET /auth/google/callback

Handle Google OAuth callback.

**Query Parameters:**
- `code` (str): Authorization code from Google
- `state` (str): OAuth state for verification

**Response:**
```json
{
  "status": "success",
  "provider": "google",
  "account_email": "user@example.com",
  "expires_at": "2025-01-15T11:30:00",
  "redirect_url": "http://localhost:3000/integrations?status=success&provider=google",
  "message": "Google account connected successfully!"
}
```

### GET /auth/zoom/start

Start Zoom OAuth flow.

**Response:**
```json
{
  "authorization_url": "https://zoom.us/oauth/authorize?...",
  "state": "random_state_token"
}
```

### GET /auth/zoom/callback

Handle Zoom OAuth callback.

**Query Parameters:**
- `code` (str): Authorization code from Zoom
- `state` (str): OAuth state for verification

**Response:**
```json
{
  "status": "success",
  "provider": "zoom",
  "expires_at": "2025-01-15T11:30:00",
  "message": "Zoom account connected successfully. You can close this window."
}
```

### GET /auth/connections

Get list of active OAuth connections.

**Response:**
```json
{
  "connections": [
    {
      "provider": "google",
      "account_email": "user@example.com",
      "scopes": "https://www.googleapis.com/auth/drive.readonly ...",
      "expires_at": "2025-01-15T11:30:00",
      "expires_in_seconds": 3600,
      "status": "active"
    }
  ]
}
```

### POST /auth/{provider}/disconnect

Disconnect OAuth provider.

**Path Parameters:**
- `provider` (str): `google` | `zoom`

**Response:**
```json
{
  "status": "success",
  "message": "Google disconnected"
}
```

---

## Upload

### POST /upload/upload-feedback

Upload customer feedback files for ingestion.

**Supports:** CSV, PDF, DOC/DOCX, TXT files

**Request:** multipart/form-data with files

**Response:**
```json
{
  "total_files": 3,
  "successful_files": 3,
  "failed_files": 0,
  "total_feedback_items": 156,
  "errors": [],
  "message": "Successfully processed all 3 file(s)"
}
```

### GET /upload/upload/supported-formats

Get list of supported file formats for feedback upload.

**Response:**
```json
{
  "supported_formats": [
    {
      "format": "CSV",
      "extensions": [".csv"],
      "mime_types": ["text/csv"],
      "description": "CSV file with 'feedback' or 'text' column",
      "example_columns": ["feedback", "customer", "date"]
    },
    {
      "format": "PDF",
      "extensions": [".pdf"],
      "mime_types": ["application/pdf"],
      "description": "PDF document with text content"
    }
  ],
  "max_file_size": "50MB",
  "max_files_per_upload": 10
}
```

---

## Ingest

### POST /ingest/slack

Ingest Slack data (demo or live based on DEMO_MODE).

**Response:**
```json
{
  "status": "completed",
  "message": "Ingested 42 Slack messages",
  "count": 42
}
```

### POST /ingest/jira

Ingest JIRA data (demo or live based on DEMO_MODE).

**Response:**
```json
{
  "status": "completed",
  "message": "Ingested 15 Jira issues",
  "count": 15
}
```

### POST /ingest/gdocs

Ingest Google Docs data.

**Request Body:**
```json
{
  "mode": "demo",
  "folder_ids": ["folder_id_1", "folder_id_2"]
}
```

**Response:**
```json
{
  "status": "completed",
  "message": "Ingested 23 Google Docs chunks",
  "count": 23
}
```

### POST /ingest/zoom

Ingest Zoom transcript data.

**Request Body:**
```json
{
  "mode": "demo",
  "start_date": "2025-01-01",
  "end_date": "2025-01-15",
  "user_id": "user@example.com"
}
```

**Response:**
```json
{
  "status": "completed",
  "message": "Ingested 18 Zoom transcript chunks",
  "count": 18
}
```

### GET /ingest/sources/summary

Get summary of feedback items by source.

**Response:**
```json
{
  "sources": [
    {
      "source": "slack",
      "count": 156,
      "last_ingested_at": "2025-01-15T10:30:00"
    },
    {
      "source": "gdoc",
      "count": 42,
      "last_ingested_at": "2025-01-14T16:20:00"
    }
  ],
  "total_count": 198
}
```

---

## Customers

### GET /customers

List all customers who have contributed to insights.

**Response:**
```json
{
  "customers": [
    {
      "name": "Acme Corp",
      "insight_count": 12,
      "feedback_count": 45
    }
  ],
  "total_customers": 1
}
```

### GET /customers/{customer_name}/insights

Get all insights for a specific customer.

**Path Parameters:**
- `customer_name` (str): Customer name

**Response:**
```json
{
  "customer": "Acme Corp",
  "insights": [
    {
      "id": "uuid",
      "title": "API Rate Limiting Issues",
      "description": "...",
      "severity": "high",
      "priority_score": 85,
      "effort": "medium",
      "impact": "...",
      "recommendation": "...",
      "feedback_count": 8
    }
  ],
  "count": 1
}
```

---

## JIRA VOC Scoring

### POST /jira/tickets

Create a new JIRA ticket.

**Request Body:**
```json
{
  "jira_key": "PROD-123",
  "title": "Implement API rate limiting enhancements",
  "description": "Based on customer feedback...",
  "status": "BACKLOG",
  "priority": "HIGH",
  "assignee": "john.doe",
  "reporter": "pm@company.com",
  "labels": ["api", "performance"],
  "epic_key": "PROD-100",
  "story_points": 8
}
```

**Response:**
```json
{
  "id": "uuid",
  "jira_key": "PROD-123",
  "title": "Implement API rate limiting enhancements",
  "description": "Based on customer feedback...",
  "status": "BACKLOG",
  "priority": "HIGH",
  "assignee": "john.doe",
  "reporter": "pm@company.com",
  "labels": ["api", "performance"],
  "epic_key": "PROD-100",
  "story_points": 8,
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:30:00"
}
```

### GET /jira/tickets

List JIRA tickets with VOC scores.

**Query Parameters:**
- `status` (str, optional): Filter by status
- `min_voc_score` (float, optional): Minimum VOC score
- `sort_by` (str): `voc_score` | `created_at` | `priority` (default: `voc_score`)

**Response:**
```json
[
  {
    "ticket": {
      "id": "uuid",
      "jira_key": "PROD-123",
      "title": "...",
      "status": "BACKLOG",
      "priority": "HIGH",
      "created_at": "2025-01-15T10:30:00",
      "updated_at": "2025-01-15T10:30:00"
    },
    "voc_score": {
      "ticket_id": "uuid",
      "customer_count": 23,
      "total_acv": 500000,
      "feedback_volume": 45,
      "ent_customer_count": 2,
      "mm_customer_count": 3,
      "smb_customer_count": 1,
      "customer_score": 85.0,
      "acv_score": 90.0,
      "segment_score": 88.0,
      "volume_score": 75.0,
      "voc_score": 87.5,
      "recommended_priority": "HIGH",
      "calculated_at": "2025-01-15T10:35:00"
    },
    "matched_insights": [
      {
        "insight_id": "uuid",
        "insight_title": "API Rate Limiting Issues",
        "similarity_score": 0.92,
        "confidence": "high",
        "is_confirmed": 1
      }
    ]
  }
]
```

### GET /jira/tickets/{ticket_key}

Get a specific JIRA ticket with VOC score.

**Path Parameters:**
- `ticket_key` (str): JIRA ticket key (e.g., PROD-123)

**Response:** Same as list tickets, single object

### POST /jira/tickets/{ticket_key}/calculate-voc

Calculate VOC score for a specific ticket.

**Path Parameters:**
- `ticket_key` (str): JIRA ticket key

**Query Parameters:**
- `similarity_threshold` (float): Minimum similarity for insight matching (default: 0.6)

**Response:**
```json
{
  "ticket_id": "uuid",
  "customer_count": 23,
  "total_acv": 500000,
  "feedback_volume": 45,
  "ent_customer_count": 2,
  "mm_customer_count": 3,
  "smb_customer_count": 1,
  "customer_score": 85.0,
  "acv_score": 90.0,
  "segment_score": 88.0,
  "volume_score": 75.0,
  "voc_score": 87.5,
  "recommended_priority": "HIGH",
  "calculated_at": "2025-01-15T10:35:00"
}
```

### POST /jira/calculate-all-voc

Calculate VOC scores for all JIRA tickets.

**Query Parameters:**
- `similarity_threshold` (float): Minimum similarity for insight matching (default: 0.6)

**Response:**
```json
{
  "message": "VOC scoring completed",
  "stats": {
    "tickets_processed": 15,
    "scores_calculated": 15,
    "avg_voc_score": 72.3
  }
}
```

### POST /jira/tickets/{ticket_key}/matches/{insight_id}/confirm

Confirm or reject an insight match for a ticket.

**Path Parameters:**
- `ticket_key` (str): JIRA ticket key
- `insight_id` (str): Insight UUID

**Query Parameters:**
- `confirmed` (bool): true to confirm, false to reject

**Response:**
```json
{
  "message": "Match confirmed",
  "ticket_key": "PROD-123",
  "insight_id": "uuid",
  "is_confirmed": 1
}
```

---

## Integrations

### GET /integrations

List all integration statuses.

**Response:**
```json
[
  {
    "provider": "zoom",
    "connected": true,
    "account_email": "user@example.com",
    "scopes": "recording:read:admin",
    "expires_at": "2025-01-15T11:30:00"
  },
  {
    "provider": "google",
    "connected": false,
    "account_email": null,
    "scopes": null,
    "expires_at": null
  }
]
```

### GET /integrations/zoom/authorize

Start Zoom OAuth flow.

**Response:**
```json
{
  "authorization_url": "https://zoom.us/oauth/authorize?...",
  "state": "random_state_token"
}
```

### DELETE /integrations/zoom/disconnect

Disconnect Zoom integration.

**Response:**
```json
{
  "message": "Zoom integration disconnected successfully"
}
```

### POST /integrations/zoom/sync

Manually trigger Zoom recordings sync.

**Query Parameters:**
- `days_back` (int): Number of days back to fetch recordings (default: 30)

**Response:**
```json
{
  "message": "Zoom sync completed",
  "stats": {
    "recordings_fetched": 5,
    "transcripts_processed": 5,
    "feedback_items_created": 42
  }
}
```

### GET /integrations/google/authorize

Start Google OAuth flow.

**Response:**
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random_state_token"
}
```

### DELETE /integrations/google/disconnect

Disconnect Google integration.

**Response:**
```json
{
  "message": "Google integration disconnected successfully"
}
```

### POST /integrations/google/sync

Manually trigger Google Drive documents sync.

**Query Parameters:**
- `folder_ids` (str): Comma-separated Google Drive folder IDs (default: "")

**Response:**
```json
{
  "message": "Google Drive sync completed",
  "stats": {
    "folders_scanned": 2,
    "documents_fetched": 15,
    "chunks_created": 127
  }
}
```

---

## Competitive Intelligence

### POST /competitive/process-manual

Process manual competitive intelligence input (Manual Mode).

**Request Body:**
```json
{
  "company_name": "ProduckAI",
  "market_scope": "Product Management Software",
  "target_personas": ["Product Managers", "Product Leaders"],
  "geo_segments": ["NA", "EU"],
  "competitor_data": [
    {
      "name": "Competitor A",
      "description": "PM tool focused on roadmapping",
      "moves": [
        {
          "move": "Launched AI-powered PRD generation",
          "date": "2025-01-10",
          "source_url": "https://example.com/announcement"
        }
      ]
    }
  ],
  "time_window_months": "12"
}
```

**Response:**
```json
{
  "id": "uuid",
  "company_name": "ProduckAI",
  "market_scope": "Product Management Software",
  "target_personas": ["Product Managers", "Product Leaders"],
  "geo_segments": ["NA", "EU"],
  "competitors_researched": ["Competitor A"],
  "insights_generated": ["uuid1", "uuid2"],
  "status": "completed",
  "error_message": null,
  "started_at": "2025-01-15T10:00:00",
  "completed_at": "2025-01-15T10:05:00"
}
```

### POST /competitive/process-auto

Process auto competitive intelligence research (Auto Mode).

**Request Body:**
```json
{
  "company_name": "ProduckAI",
  "market_scope": "Product Management Software",
  "competitor_names": ["Competitor A", "Competitor B"],
  "target_personas": ["Product Managers"],
  "geo_segments": ["Global"],
  "time_window_months": "12"
}
```

**Response:** Same as process-manual

### GET /competitive/sessions

List competitive intelligence research sessions.

**Query Parameters:**
- `limit` (int): Maximum sessions to return (default: 20)
- `offset` (int): Pagination offset (default: 0)

**Response:**
```json
[
  {
    "id": "uuid",
    "company_name": "ProduckAI",
    "market_scope": "Product Management Software",
    "target_personas": ["Product Managers"],
    "geo_segments": ["Global"],
    "competitors_researched": ["Competitor A", "Competitor B"],
    "insights_generated": ["uuid1", "uuid2"],
    "status": "completed",
    "error_message": null,
    "started_at": "2025-01-15T10:00:00",
    "completed_at": "2025-01-15T10:05:00"
  }
]
```

### GET /competitive/sessions/{session_id}

Get specific research session details.

**Path Parameters:**
- `session_id` (UUID): Research session identifier

**Response:** Same as list sessions, single object

### GET /competitive/insights

List competitive intelligence insights.

**Query Parameters:**
- `limit` (int): Maximum insights to return (default: 20)
- `offset` (int): Pagination offset (default: 0)
- `competitor_name` (str, optional): Filter by competitor name

**Response:**
```json
[
  {
    "id": "uuid",
    "title": "AI-Powered PRD Generation Threat",
    "description": "Competitor A launched AI PRD generation...",
    "impact": "May attract PM users looking for automation",
    "recommendation": "Accelerate our PRD generation roadmap",
    "severity": "high",
    "effort": "medium",
    "priority_score": 85,
    "created_at": "2025-01-15T10:05:00",
    "competitor_name": "Competitor A",
    "competitor_moves": [
      {
        "move": "Launched AI-powered PRD generation",
        "date": "2025-01-10",
        "source_url": "https://example.com/announcement"
      }
    ],
    "evidence_count": "3 sources",
    "mentions_30d": "12 mentions",
    "impacted_acv_usd": "$250k",
    "est_method": "Manual research",
    "citations": [
      {
        "title": "Product Launch Announcement",
        "url": "https://example.com/announcement",
        "date": "2025-01-10"
      }
    ]
  }
]
```

### GET /competitive/insights/{insight_id}

Get detailed competitive insight.

**Path Parameters:**
- `insight_id` (UUID): Insight identifier

**Response:** Same as list insights, single object

---

## Admin

### GET /admin/config

Get current scoring configuration.

**Response:**
```json
{
  "weights": {
    "freq_30d": 0.3,
    "acv_sum": 0.25,
    "sentiment": 0.15,
    "trend": 0.15,
    "segment": 0.15
  },
  "segment_priorities": {
    "ENT": 1.0,
    "MM": 0.7,
    "SMB": 0.4
  }
}
```

### POST /admin/weights

Update scoring weights (in-memory override).

**Request Body:**
```json
{
  "weights": {
    "freq_30d": 0.35,
    "acv_sum": 0.3,
    "sentiment": 0.15,
    "trend": 0.1,
    "segment": 0.1
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Weights updated (in-memory). Restart required for persistence.",
  "weights": {
    "freq_30d": 0.35,
    "acv_sum": 0.3,
    "sentiment": 0.15,
    "trend": 0.1,
    "segment": 0.1
  }
}
```

---

## Search

### GET /search

Unified search across feedback and themes using full-text search.

**Query Parameters:**
- `q` (str): Search query (min length: 2)
- `limit` (int): Maximum results, ≤100 (default: 20)

**Response:**
```json
[
  {
    "type": "feedback",
    "id": "uuid",
    "title": "slack feedback",
    "snippet": "We're hitting rate limits constantly on the API...",
    "score": 0.89
  },
  {
    "type": "theme",
    "id": "uuid",
    "title": "API Rate Limiting Issues",
    "snippet": "Customers experiencing rate limit errors during peak usage",
    "score": 1.0
  }
]
```

---

## Chat

### POST /chat

Chat with PM Copilot agent.

**Request Body:**
```json
{
  "message": "What are the top 3 issues affecting enterprise customers?",
  "selected_insight_id": "uuid",
  "conversation_history": [
    {
      "role": "user",
      "content": "Show me customer feedback"
    },
    {
      "role": "assistant",
      "content": "Here are the top customer feedback themes..."
    }
  ]
}
```

**Response:**
```json
{
  "response": "Based on your enterprise customer feedback, the top 3 issues are:\n1. API Rate Limiting (23 customers, $500k ACV)\n2. SSO Integration (15 customers, $300k ACV)\n3. Data Export (12 customers, $200k ACV)"
}
```

---

## Artifacts (Tickets)

### GET /tickets/{ticket_key}/score

Get ThemeScore for a JIRA ticket.

**Path Parameters:**
- `ticket_key` (str): JIRA ticket key (e.g., PROD-123)

**Response:**
```json
{
  "ticket_key": "PROD-123",
  "themes": [
    {
      "id": "uuid",
      "label": "API Rate Limiting Issues",
      "score": 87.5,
      "coverage": 0.85
    }
  ],
  "top_quotes": [
    {
      "text": "We're hitting rate limits constantly...",
      "source": "slack",
      "created_at": "2025-01-10T14:22:00"
    }
  ],
  "overall_score": 85.2
}
```

### POST /tickets/{ticket_key}/draft_prd

Generate a PRD outline for a ticket based on related themes.

**Path Parameters:**
- `ticket_key` (str): JIRA ticket key

**Response:**
```json
{
  "ticket_key": "PROD-123",
  "prd_markdown": "# PRD: PROD-123\n\n## Problem Statement\nThis ticket addresses 3 key themes identified from customer feedback.\n\n## Related Themes\n\n### API Rate Limiting Issues (Score: 87.50)\n\n## Customer Quotes\n\n1. \"We're hitting rate limits constantly...\" - slack (2025-01-10T14:22:00)\n\n## Next Steps\n- Define requirements\n- Create technical design\n- Estimate effort\n"
}
```

---

## Notes

### URL Prefix

All endpoints use **NO `/api/v1/` prefix**. The backend serves endpoints directly at the root level or with router-specific prefixes:

- `/healthz` - Health check
- `/themes/*` - Themes/insights endpoints
- `/cluster/*` - Clustering endpoints
- `/feedback*` - Feedback endpoints
- `/auth/*` - OAuth endpoints
- `/upload/*` - Upload endpoints
- `/ingest/*` - Ingestion endpoints
- `/customers*` - Customer endpoints
- `/jira/*` - JIRA VOC scoring endpoints
- `/integrations*` - Integration management
- `/competitive/*` - Competitive intelligence
- `/admin/*` - Admin configuration
- `/search*` - Search endpoint
- `/chat*` - PM Copilot chat
- `/tickets/*` - Artifact/ticket endpoints

### Authentication

OAuth 2.0 tokens are stored encrypted in the database. Active tokens are used for API calls to external services (Google Drive, Zoom).

### Error Responses

All endpoints may return standard HTTP error responses:

- `400` - Bad Request (invalid parameters)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

### Database

Uses PostgreSQL with full-text search capabilities for the `/search` endpoint.

---

**Generated:** 2025-01-15
**Backend Version:** Current production
