# MediSebi — Deployment Guide

This guide covers deploying the MediSebi frontend and backend on **separate domains/servers** (recommended for production) or together on a single server.

---

## Architecture Overview

```
  Frontend (React/Vite)          Backend (FastAPI)
  ┌──────────────────┐           ┌──────────────────┐
  │  Vercel / Netlify│ ──HTTP──► │ Railway / Render  │
  │  Cloudflare Pages│           │  Fly.io / Docker  │
  │  yourdomain.com  │           │  api.yourdomain   │
  └──────────────────┘           └──────────────────┘
                                       │
                                       ▼
                                 ┌──────────────┐
                                 │  SQLite/PG   │
                                 │  Database    │
                                 └──────────────┘
```

---

## Option A: Separate Deployment (Recommended)

### Step 1 — Deploy Backend

Choose a platform:

| Platform     | Command / Steps                                     |
|-------------|-----------------------------------------------------|
| **Railway** | Connect GitHub repo, set root to `backend/`, add env vars, deploy |
| **Render**  | New Web Service, root `backend/`, build: `pip install -r requirements.txt`, start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Fly.io**  | `fly launch` inside `backend/`, set env vars, `fly deploy` |
| **Docker**  | `docker build -t medisebi-api backend/` then `docker run -p 8000:8000 --env-file backend/.env medisebi-api` |

#### Backend `.env` (required)

```bash
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-jwt-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
DATABASE_URL=sqlite:///./medisebi.db
# PostgreSQL for production recommended:
# DATABASE_URL=postgresql://user:pass@host:5432/medisebi
CORS_ORIGINS=https://your-frontend-domain.com
OPENWEATHER_API_KEY=your-openweather-key   # Optional, for climate features
```

> **IMPORTANT**: `CORS_ORIGINS` must include your frontend domain, e.g. `https://medisebi.com`

Verify backend is running:
```bash
curl https://your-backend-api.com/health
# Should return: {"status":"healthy","service":"MediSebi","version":"1.0.0"}
```

### Step 2 — Deploy Frontend

Choose a platform:

| Platform     | Steps                                                    |
|-------------|----------------------------------------------------------|
| **Vercel**  | Connect repo, root `frontend/`, set env `VITE_API_BASE_URL`, deploy |
| **Netlify** | Connect repo, base `frontend/`, build `npm run build`, publish `dist/`, set env |
| **Cloudflare Pages** | Connect repo, root `frontend/`, build `npm run build`, output `dist/` |
| **Docker**  | `docker build -t medisebi-web frontend/`, `docker run -p 80:80 medisebi-web` |

#### Frontend Environment Variable

| Variable            | Value                                    | Description                        |
|---------------------|------------------------------------------|------------------------------------|
| `VITE_API_BASE_URL` | `https://your-backend-api.com/api/v1`   | Full URL to your backend API       |

Set this in your hosting platform's environment settings.

**Vercel Example:**
```bash
cd frontend
VITE_API_BASE_URL=https://api.yourdomain.com/api/v1 vercel --prod
```

**Netlify Example:**
Set `VITE_API_BASE_URL` in Site Settings > Environment Variables.

### Step 3 — Verify CORS

1. Open your deployed frontend URL
2. Open browser DevTools > Network tab
3. Login or make any API call
4. Verify no CORS errors in console
5. If CORS error: check `CORS_ORIGINS` in backend `.env` includes exact frontend URL (including `https://`)

---

## Option B: Single Server Deployment

Deploy both on one server using Nginx reverse proxy.

### Docker Compose (Easiest)

```bash
cd medisebi
# Edit .env files first
cp frontend/.env.production frontend/.env
cp backend/.env.example backend/.env
# Edit backend/.env and frontend/.env with your values

# Set frontend to use same-origin proxy
# In frontend/.env: VITE_API_BASE_URL=/api/v1

docker-compose up -d --build
```

### Nginx Reverse Proxy (Manual)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend (React build)
    location / {
        root /var/www/medisebi/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Build frontend
cd frontend && npm run build

# Copy dist to nginx
sudo cp -r dist/* /var/www/medisebi/frontend/dist/

# Start backend
cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000

# Reload nginx
sudo nginx -s reload
```

---

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable                    | Default                           | Required | Description                       |
|-----------------------------|-----------------------------------|----------|-----------------------------------|
| `ENVIRONMENT`               | `development`                     | No       | `production` or `development`     |
| `DEBUG`                     | `true`                            | No       | Enables Swagger docs at `/docs`   |
| `SECRET_KEY`                | *(none)*                          | **Yes**  | JWT signing key (min 32 chars)    |
| `ALGORITHM`                 | `HS256`                           | No       | JWT algorithm                     |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| `30`                             | No       | Access token TTL                  |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7`                               | No       | Refresh token TTL                 |
| `DATABASE_URL`              | `sqlite:///./medisebi.db`         | No       | Database connection string        |
| `CORS_ORIGINS`              | `*`                               | **Yes*** | Comma-separated allowed origins   |
| `OPENWEATHER_API_KEY`       | *(none)*                          | No       | For climate intelligence features |
| `HOST`                      | `0.0.0.0`                         | No       | Server bind address               |
| `PORT`                      | `8000`                            | No       | Server port                       |

*\* Required when frontend and backend are on different domains*

### Frontend (`frontend/.env.production`)

| Variable            | Example                                  | Description                        |
|---------------------|------------------------------------------|------------------------------------|
| `VITE_API_BASE_URL` | `https://api.yourdomain.com/api/v1`     | Full URL to backend API            |

> For same-domain deployment: set to `/api/v1` (Nginx proxy handles routing)

---

## Production Checklist

- [ ] Backend `SECRET_KEY` set to a strong random string (32+ chars)
- [ ] `DEBUG=false` in production
- [ ] `CORS_ORIGINS` set to exact frontend URL(s)
- [ ] `DATABASE_URL` points to PostgreSQL (not SQLite) for production
- [ ] `VITE_API_BASE_URL` in frontend points to backend API
- [ ] HTTPS enabled on both domains
- [ ] `OPENWEATHER_API_KEY` set for climate features (optional)
- [ ] Swagger docs disabled in production (`DEBUG=false` removes `/docs`)
- [ ] Database backups configured

---

## Quick Start (Development)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`, API proxy to `http://localhost:8000`.
