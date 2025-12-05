# Install Docker Desktop for macOS

## Quick Install (2 minutes)

### Option 1: Download Directly
1. **Download Docker Desktop**: https://www.docker.com/products/docker-desktop/
2. Click "Download for Mac" (Apple Silicon version)
3. Open the downloaded `Docker.dmg` file
4. Drag Docker to Applications folder
5. Open Docker from Applications
6. Accept the license agreement
7. Wait for Docker to start (you'll see a whale icon in your menu bar)

### Option 2: Using Homebrew (if Option 1 failed)
```bash
brew install --cask docker
```
Then open Docker from Applications or Spotlight.

## After Installation

Once Docker Desktop is running (whale icon in menu bar):

```bash
# Verify Docker is working
docker --version
docker compose version

# Then run ProduckAI
cd /Users/rohitsaraf/claude-code/produckai
make up
make migrate
make seed
make cluster

# Open in browser
open http://localhost:3000
```

## Alternative: Run Without Docker (Advanced)

If you prefer not to use Docker, you can run services locally:

### Install Requirements
```bash
# PostgreSQL with pgvector
brew install postgresql@16
brew install pgvector

# Redis
brew install redis

# Python 3.11
brew install python@3.11

# Node.js 20
brew install node@20
```

### Setup Services
```bash
# Start PostgreSQL
brew services start postgresql@16

# Start Redis
brew services start redis

# Setup Python environment
cd apps/api
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup Frontend
cd ../web
npm install
```

### Run Services
```bash
# Terminal 1: API
cd apps/api
source venv/bin/activate
uvicorn apps.api.main:app --reload --port 8000

# Terminal 2: Worker
cd apps/api
source venv/bin/activate
celery -A apps.worker.celery_app worker --loglevel=info

# Terminal 3: Web
cd apps/web
npm run dev

# Terminal 4: Run migrations and seed
cd apps/api
source venv/bin/activate
alembic upgrade head
python -m apps.api.scripts.seed_demo
python -m apps.api.scripts.run_clustering
```

This is more complex but doesn't require Docker.

## Recommended: Use Docker

Docker is easier because it:
- ✅ Handles all dependencies automatically
- ✅ Works the same on all machines
- ✅ One command to start everything
- ✅ Easy to clean up and reset

---

**Next**: Once Docker is running, return to the terminal and run:
```bash
make up
```
