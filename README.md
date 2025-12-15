# ProduckAI – Product Management Copilot

A local-first MVP that ingests product feedback from Slack, Jira, Google Docs, and Zoom, clusters it into themes using ML, computes transparent priority scores, and surfaces insights through a web UI and Chrome extension.

## 🚀 Quick Start (Demo Mode)

Get up and running in **under 10 minutes** with the complete platform - backend API + frontend web UI:

```bash
# 1. Clone the repo
git clone https://github.com/rohitsaraff33-bit/produckai-release-v1.0.0.git produckai
cd produckai

# 2. Copy environment file (demo mode by default)
cp .env.example .env

# 3. Start all services (Postgres, Redis, API, Worker, Web UI)
make up

# 4. Wait for services to be healthy (~30s), then run migrations
make migrate

# 5. Seed demo data and run clustering
make seed
make cluster

# 6. Open the Web UI (Next.js frontend)
open http://localhost:3000

# 7. View API docs (FastAPI backend)
open http://localhost:8000/docs
```

**That's it!** You now have the **complete ProduckAI platform** running locally:
- ✅ **Backend API** at http://localhost:8000 (FastAPI)
- ✅ **Frontend Web UI** at http://localhost:3000 (Next.js)
- ✅ **48 demo feedback** items from Slack, Jira, Google Docs, and Zoom
- ✅ **Clustered themes** with priority scores
- ✅ **AI-generated insights** ready for PRD generation

---

## 🔄 Moving from Demo Data to Your Own Data

Once you've explored the demo, you can clear it and start using your own feedback data:

### Clear Demo Data

```bash
# ⚠️ WARNING: This deletes ALL data!
make seed-clear

# Then start fresh with your data
# Option 1: Upload CSV via Web UI (http://localhost:3000/upload)
# Option 2: Connect integrations (Slack, Jira, etc.) at http://localhost:3000/integrations
# Option 3: Use the API (http://localhost:8000/docs)
```

### Re-seed Demo Data

If you want to restore the demo data:

```bash
make seed       # Load demo data
make cluster    # Generate insights
```

---

## 📊 What You'll See

### Frontend Web UI (http://localhost:3000) ⭐ NEW
The complete visual interface for product managers:

**Main Dashboard**:
- **Themes Board**: Interactive cards showing top themes ranked by priority score (0-100)
- **Filters**: By severity (Critical/High/Medium/Low), customer segment (Enterprise/Mid-Market/SMB), effort (High/Medium/Low)
- **Priority Range Slider**: Filter themes by score range
- **Customer Search**: Find themes affecting specific customers

**Theme Detail View**:
- Priority score breakdown with visual indicators
- Full description and impact analysis
- Affected customers list with ACV, segment, and feedback counts
- Supporting customer quotes with timestamps
- Recommended next steps

**Integrations Page**:
- OAuth setup for Slack, Google Drive, Zoom
- Connection status and sync history
- One-click connect buttons

**Upload Page**:
- CSV file upload with drag-and-drop
- Template download
- Bulk feedback import

**Competitive Intelligence**:
- Competitor analysis dashboard
- Feature gap identification
- Market positioning insights

**Built with**: Next.js 14 (App Router), TypeScript, Tailwind CSS, SWR

### Chrome Extension (Jira Side-Panel)
- Shows ThemeScore and top quotes when viewing a Jira ticket
- "Copy PRD outline" button generates markdown with citations
- Build: `make extension-build`, then load `apps/extension/dist` in Chrome

### Backend API (http://localhost:8000/docs)
- Interactive Swagger docs (OpenAPI 3.0)
- Try `/themes`, `/search`, `/feedback`
- 50+ REST endpoints for all operations

## 🏗️ Architecture

```mermaid
graph TB
    subgraph Sources
        Slack[Slack Export/API]
        Jira[Jira API]
        GDocs[Google Docs API]
        Zoom[Zoom Cloud Recordings]
        Linear[Linear API - stub]
    end

    subgraph Ingestion
        API[FastAPI Backend]
        Worker[Celery Worker]
        PII[PII Redaction]
        Chunk[Text Chunking]
    end

    subgraph Storage
        PG[(Postgres + pgvector)]
        Redis[(Redis)]
    end

    subgraph ML Pipeline
        Embed[Sentence Transformers<br/>all-MiniLM-L6-v2]
        Cluster[KMeans/HDBSCAN Clustering]
        Label[KeyBERT + LLM Refine]
        Score[ThemeScore Calculator]
    end

    subgraph Frontend
        Web[Next.js Web UI]
        Ext[Chrome Extension]
    end

    Slack --> API
    Jira --> API
    GDocs --> API
    Zoom --> API
    Linear --> API
    API --> PII
    PII --> Chunk
    Chunk --> PG
    API --> Worker
    Worker --> Redis
    Worker --> Embed
    Embed --> PG
    Worker --> Cluster
    Cluster --> Label
    Label --> Score
    Score --> PG
    PG --> API
    API --> Web
    API --> Ext
```

## 📦 Project Structure

```
produckai/  (this repository - complete monorepo)
├── apps/
│   ├── api/          # FastAPI backend (Python 3.11)
│   │   ├── api/      # REST endpoints (~50 routes)
│   │   ├── models/   # SQLAlchemy models
│   │   ├── services/ # Business logic (clustering, scoring, etc.)
│   │   └── scripts/  # Data seeding, ingestion, clustering
│   ├── web/          # Next.js frontend (TypeScript) ⭐ OPEN SOURCE
│   │   ├── src/app/  # App router pages
│   │   ├── src/components/  # React components
│   │   └── public/   # Static assets
│   ├── worker/       # Celery workers (async tasks)
│   └── extension/    # Chrome extension (Jira integration)
├── packages/
│   └── shared/       # Shared types & scoring logic
├── infra/
│   ├── alembic/      # Database migrations
│   └── init-db.sql   # Postgres initialization
├── samples/          # Demo data (Slack/Jira/Zoom/GDocs)
├── docker-compose.yml # Full stack orchestration
├── Makefile          # 30+ dev commands
├── INSTALLATION.md   # Detailed setup guide
├── CONTRIBUTING.md   # Contribution guidelines
├── SECURITY.md       # Security policy
└── .env.example      # Environment template
```

**What's included in this repo:**
- ✅ **Complete Backend** - FastAPI + Postgres + Redis + Celery
- ✅ **Complete Frontend** - Next.js Web UI (4,171 lines of TypeScript/TSX)
- ✅ **Chrome Extension** - Jira integration
- ✅ **Docker Setup** - One command to run everything
- ✅ **Demo Data** - Sample feedback for testing
- ✅ **Comprehensive Docs** - 1,750+ lines of documentation

## 🔧 Technology Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Alembic
- **Database**: Postgres 16 + pgvector
- **Queue**: Celery + Redis
- **ML**: sentence-transformers, HDBSCAN, KeyBERT
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Extension**: Chrome MV3, Vite
- **Testing**: pytest, Playwright
- **Tooling**: Ruff, Black, mypy, pre-commit

## 🎯 ThemeScore Formula

Transparent, customizable scoring:

```
ThemeScore =
  w_f × F_norm +           # Frequency (account count, exponentially weighted)
  w_acv × ACV_norm +       # Annual Contract Value (log-scaled)
  w_sent × SentimentLift + # Negative sentiment = higher urgency
  w_seg × SegmentPriority + # ENT > MM > SMB
  w_trend × TrendMomentum - # Recent growth
  w_dup × DupPenalty       # Similarity to higher-scored themes
```

**Default weights**: {frequency: 0.35, acv: 0.30, sentiment: 0.10, segment: 0.15, trend: 0.10, duplicate: 0.10}

Adjust weights via:
- Web UI sliders (preview mode)
- API: `POST /admin/weights`
- Environment variables

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Health check |
| `/themes` | GET | List themes (filterable, sortable) |
| `/themes/{id}` | GET | Theme detail with quotes |
| `/search` | GET | Search feedback and themes |
| `/cluster/run` | POST | Trigger clustering pipeline |
| `/tickets/{key}/score` | GET | Jira ticket ThemeScore |
| `/tickets/{key}/draft_prd` | POST | Generate PRD outline |
| `/ingest/slack` | POST | Ingest Slack data (demo/live) |
| `/ingest/jira` | POST | Ingest Jira data (demo/live) |
| `/ingest/gdocs` | POST | Ingest Google Docs (demo/live) |
| `/ingest/zoom` | POST | Ingest Zoom transcripts (demo/live) |
| `/ingest/sources/summary` | GET | Summary of feedback by source |
| `/admin/config` | GET | Current scoring weights |
| `/admin/weights` | POST | Update scoring weights |

Full docs: http://localhost:8000/docs

## 🔌 Connectors

### Demo Mode (Default)
Uses sample files in `/samples/`:
- `samples/slack/*.jsonl` - Fake Slack messages
- `samples/jira/*.json` - Fake Jira issues
- `samples/gdocs/*.md` - Sample Google Docs (markdown)
- `samples/zoom/*.vtt` - Sample Zoom transcripts (VTT format)

No API keys needed. Runs fully offline.

### Live Mode

#### Slack
1. Create a Slack app at https://api.slack.com/apps
2. Add scopes: `channels:history`, `channels:read`, `users:read`
3. Install to workspace, copy Bot Token
4. Update `.env`:
   ```
   DEMO_MODE=false
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_CHANNELS=general,product-feedback
   ```
5. Run: `make ingest-slack`

#### Jira
1. Generate API token at https://id.atlassian.com/manage-profile/security/api-tokens
2. Update `.env`:
   ```
   DEMO_MODE=false
   JIRA_URL=https://your-domain.atlassian.net
   JIRA_EMAIL=you@company.com
   JIRA_API_TOKEN=your-token
   JIRA_PROJECT_KEYS=PROD,ENG
   ```
3. Run: `make ingest-jira`

#### Google Docs
Ingest product specs, PRDs, and other documents stored in Google Drive.

**Features**:
- Chunks documents by headings and token windows (~500 tokens with 50 token overlap)
- Preserves heading structure for better context
- PII redaction (emails, phones, URLs)
- Maps documents to accounts via owner email domain

**Live Mode Setup**:
1. Create a Google Cloud project at https://console.cloud.google.com
2. Enable Google Drive API and Google Docs API
3. Create OAuth 2.0 credentials (Desktop app)
4. Run OAuth flow to get refresh token:
   ```bash
   # Use Google OAuth Playground or run local OAuth flow
   # Scopes needed:
   # - https://www.googleapis.com/auth/drive.readonly
   # - https://www.googleapis.com/auth/documents.readonly
   ```
5. Update `.env`:
   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_REFRESH_TOKEN=your-refresh-token
   DRIVE_FOLDER_IDS=folder_id_1,folder_id_2
   ```
6. Ingest from API:
   ```bash
   curl -X POST http://localhost:8000/ingest/gdocs \
     -H "Content-Type: application/json" \
     -d '{"mode": "live", "folder_ids": ["folder_id"]}'
   ```

**Demo Mode**:
```bash
# Demo mode automatically ingests from samples/gdocs/*.md
make seed  # Includes Google Docs
```

#### Zoom
Ingest customer call transcripts and meeting recordings from Zoom Cloud.

**Features**:
- Parses VTT transcripts with speaker diarization
- Chunks by time (60-120s segments)
- Extracts speaker tags and timestamps
- Optional filler word removal (uh, um)
- PII redaction before embedding
- Maps meetings to accounts via participant email domains

**Live Mode Setup**:
1. Create a Zoom Server-to-Server OAuth app at https://marketplace.zoom.us/develop/create
2. Add scope: `recording:read:admin` (or `recording:read` for user-level)
3. Activate the app and get credentials
4. Update `.env`:
   ```
   ZOOM_JWT_OR_OAUTH_TOKEN=your-oauth-access-token
   ZOOM_USER_ID=me  # or specific user email
   ZOOM_START_DATE=2025-01-01
   ZOOM_END_DATE=2025-12-31
   ZOOM_REMOVE_FILLERS=false  # Set to true to remove uh/um
   PII_REDACTION_ENABLED=true
   ```
5. Ingest from API:
   ```bash
   curl -X POST http://localhost:8000/ingest/zoom \
     -H "Content-Type: application/json" \
     -d '{"mode": "live", "start_date": "2025-01-01", "end_date": "2025-03-31"}'
   ```

**Demo Mode**:
```bash
# Demo mode automatically ingests from samples/zoom/*.vtt
make seed  # Includes Zoom transcripts
```

**Note**: Zoom transcripts must be enabled in your Zoom account settings (Account > Settings > Recording > Cloud recording > Advanced cloud recording settings > Audio transcript).

#### Linear (Stub)
Coming in v2. Client interface exists at `apps/api/connectors/linear.py`.

## 🧪 Testing

```bash
# Run all tests
make test

# With coverage
make test-cov

# Watch mode
make test-watch

# Lint
make lint

# Format
make format
```

## 🐳 Docker Commands

```bash
make up          # Start services
make down        # Stop services
make logs        # Follow all logs
make logs-api    # Follow API logs only
make ps          # Show running services
make shell-api   # Shell into API container
make shell-db    # Open psql
make clean       # Remove containers and volumes
```

## 🗄️ Database Migrations

```bash
# Apply migrations
make migrate

# Create new migration
make migrate-create MSG="add sentiment column"

# Rollback
make migrate-down
```

## 🔐 Security & Privacy

- **Read-only OAuth scopes**: Connectors never write/delete
- **PII redaction**: Regex-based email/phone scrubbing (configurable)
- **No raw audio storage**: Only text embeddings
- **Local-first**: Demo mode runs fully offline
- **JWT auth**: Extension requires valid token
- **Secrets**: Never commit `.env` (use `.env.example`)

## 🚢 Deployment (Future)

For production:
1. Use managed Postgres (AWS RDS, Supabase, Neon)
2. Enable pgvector extension
3. Use managed Redis (ElastiCache, Upstash)
4. Deploy API/Worker to containers (ECS, Cloud Run, Fly.io)
5. Deploy Web to Vercel/Netlify
6. Set environment variables via secrets manager
7. Enable OTEL_ENABLED=true with your observability backend

## 📝 Development Workflow

```bash
# Daily workflow
make up                    # Start services
make logs-api             # Watch logs
make test-watch           # TDD

# After changing models
make migrate-create MSG="your change"
make migrate

# After ingesting new data
make cluster

# Before committing
make lint
make format
make test
```

## 🐛 Troubleshooting

**Services won't start?**
```bash
make clean
make build
make up
```

**Database errors?**
```bash
make shell-db
# Check tables: \dt
# Check extensions: \dx
```

**Clustering not working?**
- Ensure at least 20 feedback items exist (check `CLUSTERING_MIN_FEEDBACK_COUNT`)
- Check worker logs: `make logs-worker`

**Port conflicts?**
- Edit `docker-compose.yml` to change port mappings

## 📚 Additional Resources

- [Architecture.md](./Architecture.md) - Detailed system design
- [API Docs](http://localhost:8000/docs) - Interactive Swagger
- [Scoring Deep Dive](./packages/shared/scoring.py) - ThemeScore implementation

## 📧 Contact & Community

### Get in Touch
- **Creator**: Rohit Saraf ([rohitsaraff33@gmail.com](mailto:rohitsaraff33@gmail.com))
- **GitHub Repository**: https://github.com/rohitsaraff33-bit/produckai-release-v1.0.0
- **GitHub Issues**: https://github.com/rohitsaraff33-bit/produckai-release-v1.0.0/issues
- **GitHub Discussions**: https://github.com/rohitsaraff33-bit/produckai-release-v1.0.0/discussions

### Vision & Community
This project was built **for product managers, by product managers**. The goal is to create a thriving open source community where builders enhance integrations, improve clustering algorithms, and share learnings so the entire PM community benefits.

**We especially welcome contributions in:**
- 🔌 **Integration enhancements** - New data sources (Linear, Notion, Intercom, Zendesk)
- 🧠 **ML & Clustering** - Alternative algorithms, multi-language models, sentiment analysis
- 📊 **Analytics & Scoring** - New VOC dimensions, custom formulas, trend detection
- 🎨 **Frontend & UX** - Web UI improvements, mobile views, accessibility
- 📚 **Documentation** - Tutorials, guides, translations

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

---

## 🤝 Contributing

We welcome all contributions! Here's how to get started:

1. **Fork the repository** on GitHub
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes** and test locally with `make test`
4. **Format your code**: `make format && make lint`
5. **Commit your changes**: `git commit -m "feat: add Linear integration"`
6. **Push and create a PR**: `git push origin feature/your-feature-name`

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

---

## 🔐 Security

We take security seriously. If you discover a security vulnerability:
- **DO NOT** open a public issue
- Email [rohitsaraff33@gmail.com](mailto:rohitsaraff33@gmail.com) with details
- See [SECURITY.md](SECURITY.md) for our security policy and responsible disclosure process

---

## 📚 Additional Documentation

- [INSTALLATION.md](INSTALLATION.md) - Detailed installation guide (Docker + manual setup)
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines and development workflow
- [SECURITY.md](SECURITY.md) - Security policy and vulnerability reporting
- [API Docs](http://localhost:8000/docs) - Interactive Swagger documentation (when running)

---

## 🚀 Related Projects

- **ProduckAI MCP Server**: Claude Desktop integration for natural language interaction with this backend
  - GitHub: https://github.com/rohitsaraff33-bit/produckai-mcp-server
  - PyPI: https://pypi.org/project/produckai-mcp-server/
  - Install: `pip install produckai-mcp-server`

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built with these amazing open source projects:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Sentence Transformers](https://www.sbert.net/) - State-of-the-art sentence embeddings
- [PostgreSQL](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search
- [Next.js](https://nextjs.org/) - React framework for production
- [Celery](https://docs.celeryq.dev/) - Distributed task queue

---

**Built with ❤️ for product managers who deserve better tools.**

**Let's build the future of product management together!** 🚀
