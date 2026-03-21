# 🚀 Hosting your SEO Analyst Backend

This guide explains how to take your development environment to the web.

## 1. Hosting Providers
We recommend the following for quick, affordable FastAPI hosting:
- **Render.com** (Easiest / Great free tier)
- **Railway.app** (Powerful performance/database)
- **DigitalOcean** (Scalable/Reliable)

### 🚀 Deploying to Render:
1.  **Connect your Repo:** Sign up for Render and link your GitHub repository.
2.  **Create Service:** Choose "New" -> "Web Service".
3.  **Root Directory:** Set to `./backend`.
4.  **Runtime:** Python.
5.  **Build Command:** `pip install -r requirements.txt`.
6.  **Start Command:** `uvicorn main:app --host 0.0.0.0 --port 10000`.

## 2. Setting Environment Variables
Do NOT use a `.env` file for production! Set these in the Render/Railway dashboard:
- `GROQ_API_KEY`: llama-3.3-70b-versatile
- `SUPABASE_URL`: Your project URL.
- `SUPABASE_KEY`: Your service role key.
- `SUPABASE_DB_URL`: Postgres connection URI.

## 3. Database Syncing
Ensure you've run the `scripts/setup_db.py` once locally to initialize your Supabase tables.

## 4. Extension Finalization
After your backend is live (e.g., `https://seo-analyst.onrender.com`):
1.  Open `/extension/background.js` and `/extension/popup.js`.
2.  Search-and-replace `http://localhost:8000` with your new production URL.
3.  Refresh the extension in Chrome to point to the live cloud API.

---
**🔐 Security Tip:**
Ensure `backend/.gitignore` includes `.env` and `venv/` so you don't leak secrets or bloat your repo.
