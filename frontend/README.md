# ConnectX Frontend (Vercel Deployment)

This directory contains the ConnectX web client configured for high-speed edge CDN deployment on Vercel.

## 🚀 One-Click Vercel Deployment

1. Go to [Vercel](https://vercel.com).
2. Click **Add New Project** and import this repository.
3. Set the **Root Directory** to `frontend` (or leave default root `/`, as root `vercel.json` maps directly to `frontend`).
4. Framework Preset: **Other**.
5. Click **Deploy**.

## 🔗 Connecting to Railway Backend

In the deployed Vercel application, input your Railway backend endpoint URL (e.g. `https://your-service.up.railway.app`) in the configuration panel to connect real-time WebSockets and APIs.
