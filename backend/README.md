# ConnectX Backend (Railway Deployment)

This directory contains the complete real-time Python/Flask-SocketIO backend service configured for Railway.

## 🚀 One-Click Railway Deployment

1. Create a new project on [Railway.app](https://railway.app).
2. Choose **Deploy from GitHub repo**.
3. Select this repository.
4. Set the **Root Directory** to `backend` (or leave as root `/`).
5. Add a **PostgreSQL** database plugin on Railway.
6. Railway automatically supplies `DATABASE_URL` and `PORT`.
7. Your real-time WebSocket backend is live at `https://your-service.up.railway.app`!

## ⚙️ Environment Variables

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Secret encryption key | `connectx_secret_key_prod` |
| `FLASK_ENV` | Environment mode | `production` |
| `DATABASE_URL` | PostgreSQL/SQLite connection | Managed by Railway |
| `PORT` | Container network port | Managed by Railway (`5000`) |
| `HOST` | Server host binding | `0.0.0.0` |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origins | `*` (or your Vercel URL) |
| `ADMIN_PASSWORD` | Default admin password | `Admin@123456` |
