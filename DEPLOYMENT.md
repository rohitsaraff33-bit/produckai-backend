# ProduckAI Deployment Guide

This guide covers deploying ProduckAI to production for PM feedback.

## Architecture

- **Frontend**: Next.js → Netlify
- **Backend**: FastAPI + PostgreSQL + Redis → Railway/Render
- **Reason**: Netlify doesn't support long-running APIs, databases, or workers

---

## Option 1: Railway (Recommended - Easiest)

### Step 1: Deploy Backend to Railway

1. **Create Railway Account**
   - Go to https://railway.app
   - Sign up with GitHub

2. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   railway login
   ```

3. **Create New Project**
   ```bash
   cd /Users/rohitsaraf/claude-code/produckai
   railway init
   # Select "Create new project"
   # Name it "produckai-backend"
   ```

4. **Add Database Services**
   ```bash
   # Add PostgreSQL with pgvector
   railway add postgresql

   # Add Redis
   railway add redis
   ```

5. **Set Environment Variables in Railway Dashboard**
   - Go to https://railway.app/dashboard
   - Select your project
   - Click on "Variables"
   - Add:
     ```
     DATABASE_URL=${POSTGRESQL_URL}
     REDIS_URL=${REDIS_URL}
     DEMO_MODE=true
     CORS_ORIGINS=https://your-app.netlify.app,http://localhost:3000
     ```

6. **Deploy API**
   ```bash
   # Railway will auto-detect Dockerfile
   railway up

   # Get your API URL
   railway domain
   # Example: https://produckai-backend-production.up.railway.app
   ```

7. **Run Database Migrations**
   ```bash
   railway run alembic upgrade head
   ```

8. **Load Demo Data**
   ```bash
   railway run python apps/api/scripts/seed_demo_data.py
   railway run python apps/api/scripts/run_clustering.py
   ```

### Step 2: Deploy Frontend to Netlify

1. **Create Netlify Account**
   - Go to https://netlify.com
   - Sign up with GitHub

2. **Connect Repository**
   - Click "Add new site" → "Import existing project"
   - Connect your GitHub repository
   - Select the ProduckAI repo

3. **Configure Build Settings**
   - Base directory: `apps/web`
   - Build command: `npm run build`
   - Publish directory: `apps/web/.next`
   - Node version: `18`

4. **Set Environment Variables**
   - Go to Site settings → Environment variables
   - Add:
     ```
     NEXT_PUBLIC_API_URL=https://your-railway-api.railway.app
     NODE_VERSION=18
     ```

5. **Deploy**
   - Click "Deploy site"
   - Wait for build to complete
   - Get your URL: `https://your-app.netlify.app`

6. **Update Backend CORS**
   - Go back to Railway dashboard
   - Update `CORS_ORIGINS` to include your Netlify URL
   - Redeploy backend

---

## Option 2: Render (Alternative)

### Deploy to Render (All-in-One)

1. **Create Render Account**: https://render.com

2. **Create PostgreSQL Database**
   - New → PostgreSQL
   - Name: `produckai-db`
   - Plan: Free
   - Note down the connection string

3. **Create Redis Instance**
   - New → Redis
   - Name: `produckai-redis`
   - Plan: Free

4. **Create Web Service (API)**
   - New → Web Service
   - Connect GitHub repo
   - Settings:
     - Root Directory: `.`
     - Environment: Docker
     - Dockerfile Path: `Dockerfile.api`
     - Plan: Starter ($7/mo for always-on)
   - Environment Variables:
     ```
     DATABASE_URL=<your-postgres-url>
     REDIS_URL=<your-redis-url>
     DEMO_MODE=true
     CORS_ORIGINS=https://your-app.onrender.com
     ```

5. **Create Web Service (Frontend)**
   - New → Static Site
   - Root Directory: `apps/web`
   - Build Command: `npm install && npm run build`
   - Publish Directory: `apps/web/.next`
   - Environment Variables:
     ```
     NEXT_PUBLIC_API_URL=https://your-api.onrender.com
     ```

6. **Create Background Worker**
   - New → Background Worker
   - Command: `celery -A apps.worker.celery_app worker --loglevel=info`

---

## Option 3: Vercel (Alternative)

Vercel is optimized for Next.js but requires serverless backend approach.

1. **Deploy Frontend to Vercel**
   ```bash
   npm install -g vercel
   cd apps/web
   vercel
   ```

2. **Deploy Backend Separately**
   - Use Railway or Render for backend
   - Point Vercel environment variable to backend URL

---

## Post-Deployment Checklist

- [ ] Frontend loads successfully
- [ ] Can see demo insights
- [ ] Can access integrations page
- [ ] Can upload files (if testing file upload)
- [ ] Can run competitive intelligence
- [ ] Check browser console for API errors
- [ ] Test on mobile device

---

## Cost Estimates

### Railway (Recommended)
- **Free tier**: $5 credit/month (sufficient for testing)
- **Hobby**: $5-20/month for production
- **PostgreSQL + Redis**: Included in credit

### Netlify
- **Free tier**: 100GB bandwidth, 300 build minutes/month
- **Pro**: $19/month (if you need more)

### Total for Testing: **$0-5/month**
### Total for Production: **$20-40/month**

---

## Troubleshooting

### Frontend can't reach API
- Check `NEXT_PUBLIC_API_URL` is set correctly
- Check CORS settings in backend include frontend URL
- Check browser console for errors

### Database connection fails
- Verify `DATABASE_URL` format
- Ensure PostgreSQL has pgvector extension
- Run migrations: `railway run alembic upgrade head`

### No insights showing
- Run clustering script: `railway run python apps/api/scripts/run_clustering.py`
- Check API logs for errors

---

## Security Notes for Production

Before sharing with other PMs:

1. **Add Authentication** (if needed)
   - Consider adding basic auth or OAuth
   - Railway supports environment-based auth

2. **API Rate Limiting**
   - Add rate limiting to prevent abuse

3. **Environment Variables**
   - Never commit API keys to Git
   - Use platform environment variable systems

4. **Database Backups**
   - Railway and Render offer automatic backups
   - Enable them in dashboard

---

## Quick Start (Railway + Netlify)

```bash
# 1. Deploy backend
railway login
railway init
railway add postgresql
railway add redis
railway up

# 2. Setup database
railway run alembic upgrade head
railway run python apps/api/scripts/seed_demo_data.py

# 3. Get backend URL
railway domain
# Copy this URL

# 4. Deploy frontend on Netlify
# - Go to netlify.com
# - Import from GitHub
# - Set NEXT_PUBLIC_API_URL to Railway URL
# - Deploy

# Done! Share your Netlify URL with PMs
```
