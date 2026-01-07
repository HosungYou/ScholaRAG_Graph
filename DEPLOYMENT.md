# ScholaRAG_Graph Deployment Guide

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│     Vercel      │ ──── │     Render      │ ──── │   PostgreSQL    │
│  (Frontend)     │      │   (Backend)     │      │   (pgvector)    │
│  Next.js 14     │      │   FastAPI       │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

## 1. Database Setup (Render PostgreSQL)

### Create PostgreSQL Database

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "PostgreSQL"
3. Configure:
   - **Name**: `scholarag-graph-db`
   - **Region**: Oregon (or closest to your users)
   - **Plan**: Starter ($7/month) or Free (90-day limit)
   - **PostgreSQL Version**: 16
4. After creation, note the **Internal Database URL** for backend connection

### Enable pgvector Extension

Connect to your database and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 2. Backend Deployment (Render Web Service)

### Option A: Deploy via render.yaml (Recommended)

1. Push code to GitHub
2. Go to Render Dashboard → "New" → "Blueprint"
3. Connect your GitHub repository
4. Render will automatically detect `render.yaml` and create services

### Option B: Manual Deployment

1. Go to Render Dashboard → "New" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - **Name**: `scholarag-graph-api`
   - **Region**: Oregon
   - **Branch**: main
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

### Environment Variables (Render)

Add these in Render Dashboard → Environment:

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `ANTHROPIC_API_KEY` | Claude API key | Yes (or other LLM) |
| `OPENAI_API_KEY` | OpenAI API key | Optional |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | Yes |
| `DEBUG` | Set to `false` | Recommended |

Example `CORS_ORIGINS`:
```
https://scholarag-graph.vercel.app,http://localhost:3000
```

## 3. Frontend Deployment (Vercel)

### Deploy to Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "Add New" → "Project"
3. Import from GitHub repository
4. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`

### Environment Variables (Vercel)

Add in Vercel Dashboard → Settings → Environment Variables:

| Variable | Value | Environment |
|----------|-------|-------------|
| `NEXT_PUBLIC_API_URL` | `https://scholarag-graph-api.onrender.com` | Production |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Development |

## 4. Post-Deployment Checklist

- [ ] Database pgvector extension enabled
- [ ] Database migrations run successfully
- [ ] Backend health check passes (`/health` endpoint)
- [ ] Frontend can connect to backend API
- [ ] CORS configured correctly
- [ ] LLM API key working (test chat endpoint)

## 5. Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file from .env.example
cp ../.env.example .env
# Edit .env with your values

# Run server
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install

# Create .env.local
cp .env.example .env.local
# Edit .env.local with your backend URL

# Run dev server
npm run dev
```

## 6. Troubleshooting

### CORS Errors

1. Check `CORS_ORIGINS` includes your frontend URL
2. Ensure no trailing slashes in origins
3. Verify backend is redeployed after changes

### Database Connection Issues

1. Verify `DATABASE_URL` format: `postgresql://user:pass@host:port/dbname`
2. Check IP allowlist in Render PostgreSQL settings
3. Ensure pgvector extension is installed

### LLM API Errors

1. Verify API key is set correctly (no quotes, no spaces)
2. Check API key permissions and quotas
3. Review backend logs for specific error messages

## 7. URLs

After deployment, your services will be available at:

- **Frontend**: `https://scholarag-graph.vercel.app`
- **Backend API**: `https://scholarag-graph-api.onrender.com`
- **API Docs**: `https://scholarag-graph-api.onrender.com/docs`
- **Health Check**: `https://scholarag-graph-api.onrender.com/health`
