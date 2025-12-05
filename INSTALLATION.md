# Installation Guide - ProduckAI Backend

This guide will help you set up the ProduckAI backend (FastAPI + Postgres + Redis) on your local machine.

## 📋 Prerequisites

- **Docker** & **Docker Compose** (recommended - easiest setup)
- **OR** Python 3.11+, Postgres 16+, Redis 7+ (manual setup)
- **Minimum**: 4GB RAM, 2GB free disk space
- **Recommended**: 8GB RAM, 5GB free disk space (for ML models)

---

## 🚀 Quick Start (Docker - Recommended)

Get up and running in **under 10 minutes** with Docker:

### 1. Clone the Repository

```bash
git clone https://github.com/rohitsaraff33-bit/produckai-release-v1.0.0.git produckai
cd produckai
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your preferred editor
# For demo mode, no changes needed!
nano .env
```

### 3. Start All Services

```bash
# Start Postgres, Redis, API, Worker, and Web UI
make up

# Wait ~30 seconds for services to be healthy
# Check status
make ps
```

### 4. Run Database Migrations

```bash
make migrate
```

### 5. Seed Demo Data

```bash
# Seed with fake feedback from Slack, Jira, Google Docs, Zoom
make seed

# Run clustering to generate themes
make cluster
```

### 6. Verify Installation

```bash
# Check API health
curl http://localhost:8000/healthz

# Open API docs
open http://localhost:8000/docs

# Open Web UI
open http://localhost:3000
```

**🎉 You're done!** The backend is now running with demo data.

---

## 🐳 Docker Services

When you run `make up`, Docker Compose starts these services:

| Service | Port | Description |
|---------|------|-------------|
| **postgres** | 5432 | Postgres 16 + pgvector extension |
| **redis** | 6379 | Redis 7 (for Celery task queue) |
| **api** | 8000 | FastAPI backend (auto-reload enabled) |
| **worker** | - | Celery worker (clustering, embeddings) |
| **beat** | - | Celery beat (scheduled tasks) |
| **web** | 3000 | Next.js web UI (optional) |

---

## 🔧 Manual Installation (Without Docker)

If you prefer to run services natively:

### 1. Install System Dependencies

**macOS:**
```bash
brew install python@3.11 postgresql@16 redis
brew services start postgresql@16
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv postgresql-16 postgresql-16-pgvector redis-server
sudo systemctl start postgresql
sudo systemctl start redis
```

### 2. Set Up Postgres

```bash
# Create database and user
sudo -u postgres psql

CREATE DATABASE produckai;
CREATE USER produckai WITH PASSWORD 'produckai_dev_password';
GRANT ALL PRIVILEGES ON DATABASE produckai TO produckai;
\q
```

Enable pgvector extension:
```bash
psql -U produckai -d produckai -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 3. Set Up Python Environment

```bash
cd produckai
python3.11 -m venv venv
source venv/bin/activate

# Install backend dependencies
pip install -r apps/api/requirements.txt

# Install ML models (first run takes ~2 minutes)
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` to point to your local Postgres and Redis:
```bash
DATABASE_URL=postgresql://produckai:produckai_dev_password@localhost:5432/produckai
REDIS_URL=redis://localhost:6379/0
```

### 5. Run Migrations

```bash
cd apps/api
alembic upgrade head
```

### 6. Start Services

**Terminal 1 - API:**
```bash
source venv/bin/activate
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Celery Worker:**
```bash
source venv/bin/activate
celery -A apps.worker.celery_app worker --loglevel=info
```

**Terminal 3 - Celery Beat (optional):**
```bash
source venv/bin/activate
celery -A apps.worker.celery_app beat --loglevel=info
```

### 7. Seed Demo Data

```bash
python -m apps.api.scripts.seed_demo
python -m apps.api.scripts.run_clustering
```

---

## 🔌 Integrations Setup (Optional)

### Demo Mode vs Live Mode

- **Demo Mode** (`DEMO_MODE=true`): Uses sample data from `samples/` directory. No API keys needed.
- **Live Mode** (`DEMO_MODE=false`): Connects to real Slack, Jira, Google Drive, Zoom APIs.

### Slack Integration

1. Create Slack App at https://api.slack.com/apps
2. Add Bot Token Scopes:
   - `channels:history`
   - `channels:read`
   - `users:read`
3. Install to workspace and copy **Bot User OAuth Token**
4. Update `.env`:
   ```bash
   DEMO_MODE=false
   SLACK_BOT_TOKEN=xoxb-your-token-here
   SLACK_CHANNELS=general,product-feedback,support
   ```
5. Ingest: `make ingest-slack`

### Jira Integration

1. Generate API token at https://id.atlassian.com/manage-profile/security/api-tokens
2. Update `.env`:
   ```bash
   JIRA_URL=https://your-domain.atlassian.net
   JIRA_EMAIL=you@company.com
   JIRA_API_TOKEN=your-api-token
   JIRA_PROJECT_KEYS=PROD,ENG
   ```
3. Ingest: `make ingest-jira`

### Google Drive Integration

1. Create Google Cloud project at https://console.cloud.google.com
2. Enable Drive API and Docs API
3. Create OAuth 2.0 credentials (Desktop app)
4. Run OAuth flow to get refresh token
5. Update `.env`:
   ```bash
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-secret
   GOOGLE_REFRESH_TOKEN=your-refresh-token
   DRIVE_FOLDER_IDS=folder_id_1,folder_id_2
   ```
6. Ingest via API:
   ```bash
   curl -X POST http://localhost:8000/ingest/gdocs \
     -H "Content-Type: application/json" \
     -d '{"mode": "live", "folder_ids": ["your-folder-id"]}'
   ```

### Zoom Integration

1. Create Server-to-Server OAuth app at https://marketplace.zoom.us/develop/create
2. Add scope: `recording:read:admin`
3. Update `.env`:
   ```bash
   ZOOM_JWT_OR_OAUTH_TOKEN=your-access-token
   ZOOM_USER_ID=me
   ZOOM_START_DATE=2025-01-01
   ```
4. Ingest via API:
   ```bash
   curl -X POST http://localhost:8000/ingest/zoom \
     -H "Content-Type: application/json" \
     -d '{"mode": "live", "start_date": "2025-01-01", "end_date": "2025-03-31"}'
   ```

---

## 🧪 Verify Installation

### Check API Health

```bash
curl http://localhost:8000/healthz

# Expected response:
# {"status":"healthy","version":"1.0.0","demo_mode":true}
```

### Check Database

```bash
# Docker
make shell-db

# Manual
psql -U produckai -d produckai

# Run SQL
\dt  # List tables (should see feedback, themes, insights, customers, etc.)
SELECT COUNT(*) FROM feedback;  # Should see demo data if seeded
```

### Check Redis

```bash
# Docker
make shell-redis

# Manual
redis-cli

# Test
PING  # Should return PONG
```

### Check Celery Worker

```bash
# Check worker logs
make logs-worker

# Should see:
# [tasks]
#   . apps.worker.tasks.cluster_feedback
#   . apps.worker.tasks.generate_embeddings
```

---

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Clean up and rebuild
make clean
make build
make up
```

### Port Already in Use

**Error:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution:** Stop existing service or change port in `docker-compose.yml`:
```yaml
api:
  ports:
    - "8001:8000"  # Change host port to 8001
```

### Database Migration Errors

**Error:** `sqlalchemy.exc.ProgrammingError: relation "feedback" does not exist`

**Solution:** Run migrations:
```bash
make migrate
```

If that fails:
```bash
make shell-db
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
\q

make migrate
```

### Clustering Not Working

**Error:** Clustering job completes but no themes generated

**Possible causes:**
1. Less than 20 feedback items (default `CLUSTERING_MIN_FEEDBACK_COUNT`)
2. ML model not downloaded
3. Worker not running

**Solution:**
```bash
# Check feedback count
make shell-db
SELECT COUNT(*) FROM feedback;

# If < 20, seed more data
make seed

# Check worker logs
make logs-worker

# Manually trigger clustering
make cluster
```

### ML Model Download Fails

**Error:** `FileNotFoundError: sentence-transformers/all-MiniLM-L6-v2`

**Solution:**
```bash
# Pre-download model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Or change model in .env
EMBEDDING_MODEL=sentence-transformers/multi-qa-MiniLM-L6-cos-v1
```

### Out of Memory (OOM)

**Error:** Worker killed or API crashes

**Solution:** Reduce batch size in `.env`:
```bash
EMBEDDING_BATCH_SIZE=16  # Default is 32
```

Or allocate more memory to Docker:
- Docker Desktop → Settings → Resources → Memory: 8GB

---

## 📚 Next Steps

Now that your backend is running:

1. **Explore the API**: http://localhost:8000/docs
2. **View the Web UI**: http://localhost:3000
3. **Install the MCP Server**: Connect Claude Desktop to your backend
   ```bash
   pip install produckai-mcp-server
   ```
   See: https://github.com/rohitsaraff33-bit/produckai-mcp-server

4. **Customize Scoring Weights**: Edit `.env` or use the Web UI
5. **Ingest Your Own Data**: Set up Slack/Jira/Google Drive integrations

---

## 🔐 Security Best Practices

- **Never commit `.env`** - It's already in `.gitignore`
- **Use read-only API keys** - Connectors never write/delete
- **Enable PII redaction** - Set `PII_REDACTION_ENABLED=true` (default)
- **Use strong JWT secret** - Generate with: `openssl rand -base64 32`
- **Enable HTTPS in production** - Use Nginx reverse proxy or cloud load balancer

---

## 🤝 Getting Help

- **Documentation**: See [README.md](README.md) for architecture and API docs
- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) (if available)
- **GitHub Issues**: https://github.com/rohitsaraff33-bit/produckai-release-v1.0.0/issues
- **Email**: rohitsaraff33@gmail.com

---

**Built with ❤️ for product managers who deserve better tools.**
