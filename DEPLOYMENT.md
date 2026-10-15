# Deployment Guide: Nari AI

This guide walks you through deploying **Nari AI** with:
- **Backend (FastAPI)** on **Render**
- **Frontend (React + Vite)** on **Vercel**

---

## 1. Deploying the Backend on Render

### Option A: Using Render Blueprint (Automatic via `render.yaml`)
1. Push your latest code to your GitHub repository.
2. In the [Render Dashboard](https://dashboard.render.com/), click **New +** -> **Blueprint**.
3. Select your repository. Render will automatically detect [render.yaml](file:///render.yaml).
4. Fill in the environment variables prompted by the blueprint (see Environment Variables list below).
5. Click **Apply**.

---

### Option B: Manual Web Service Setup on Render
1. In the Render Dashboard, click **New +** -> **Web Service**.
2. Connect your GitHub repository.
3. Configure the following settings:
   - **Name**: `nari-backend`
   - **Language**: `Python 3`
   - **Region**: Closest to your users (e.g., `Singapore` or `Frankfurt`)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
4. Expand **Advanced** -> **Health Check Path** and set it to `/`.

---

### Backend Environment Variables (Render Dashboard)
Add these under the **Environment** tab in your Render service:

| Variable | Description | Example / Note |
|---|---|---|
| `PYTHON_VERSION` | Python runtime version | `3.11.9` |
| `MONGO_URI` | MongoDB Atlas Connection String | `mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority` |
| `MONGO_DB_NAME` | Database name | `nari` |
| `GROQ_API_KEY` | Groq Cloud API Key | `gsk_...` |
| `GROQ_MODEL` | AI model | `openai/gpt-oss-120b` |
| `GEMINI_API_KEY` | Google Gemini API Key | `AIzaSy...` (optional fallback) |
| `GOOGLE_MAPS_API_KEY` | Google Maps API Key | `AIzaSy...` |
| `FIREBASE_API_KEY` | Firebase Web API Key | `AIzaSy...` |
| `FIREBASE_SERVICE_ACCOUNT` | Entire JSON content of `serviceaccount.json` | Paste entire JSON as single string or base64 |
| `CORS_ORIGINS` | Allowed frontend origins | `*` (or `https://your-frontend.vercel.app`) |
| `SMS_PROVIDER` | SMS Gateway | `mock` (or `twilio`) |

> **Tip for `FIREBASE_SERVICE_ACCOUNT`:**
> Open your local `backend/serviceaccount.json`, copy the entire JSON content, and paste it directly into the `FIREBASE_SERVICE_ACCOUNT` value field in Render. Alternatively, encode it to base64 using `[Convert]::ToBase64String([IO.File]::ReadAllBytes('backend/serviceaccount.json'))` in PowerShell and paste the base64 string.

Once deployed, copy your Render backend URL (e.g., `https://nari-backend.onrender.com`).
Verify by opening `https://nari-backend.onrender.com/` in your browser. You should see:
```json
{
  "status": "healthy",
  "service": "Nari Women's Safety Core API",
  "version": "1.0.0"
}
```

---

## 2. Deploying the Frontend on Vercel

1. Go to [Vercel Dashboard](https://vercel.com/) and click **Add New...** -> **Project**.
2. Import your GitHub repository.
3. Configure the Project:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click **Edit** and select `nari-frontend` *(or leave as `./` since root `vercel.json` is configured)*.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Expand **Environment Variables** and add:

| Key | Value | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | `https://your-backend.onrender.com/api` | Replace with your Render URL + `/api` |

*(Note: Groq and Firebase service account keys are stored securely in backend environment variables on Render only. Never put AI API keys in frontend Vercel variables!)*

5. Click **Deploy**.

---

## 3. Important Production Notes

1. **Render Free Tier Cold Starts**: Render's free tier spins down after 15 minutes of inactivity. When a new request arrives, it may take 30–50 seconds to wake up. The frontend API client is configured with a 60-second timeout to handle this gracefully.
2. **CORS**: The backend has pre-configured wildcard and `https://*.vercel.app` origin matching, so all Vercel production and preview URLs work immediately out of the box without CORS errors.
3. **SPA Routing**: Client-side routing is handled via `vercel.json` rewriting `/(.*)` to `/index.html`, ensuring pages like `/routes`, `/emergency`, and `/profile` work on direct reload.
