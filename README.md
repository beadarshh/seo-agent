# 🚀 SEO Agent: Deep Professional Analyst

A powerful Chrome extension built for professional SEO audits. It uses **Groq (Llama 3.3)** and **Supabase (pgvector)** to analyze web pages, provide actionable text reframes, and learn your specific optimization patterns over time.

## ✨ Key Features
- **Deep Page Scanning:** Captures over 10,000 characters of content and structural data (H1-H4, Meta, Title).
- **Actionable AI Reframing:** Don't just find errors—get the exact rewritten headings and meta tags in one click.
- **RAG-Powered Memory:** "Teach" the AI by ingesting findings directly into its long-term vector memory.
- **Project Tracking:** Full History and 2-Week Performance reports integrated into the dashboard.

## 📁 Repository Structure
- **/extension**: The Chrome Extension frontend (HTML/CSS/JS).
- **/backend**: The FastAPI service (Python) handling AI logic & Database.
- **/backend/scripts**: Database setup and migration scripts.

## 🛠️ 1-Minute Project Setup

1.  **Backend Start:**
    ```bash
    cd backend
    python -m venv venv
    .\venv\Scripts\activate 
    pip install -r requirements.txt
    python scripts/setup_db.py   # <-- CRITICAL: This prepares your DB!
    uvicorn main:app --reload
    ```
2.  **Extension Start:**
    *   Load the **unpacked** extension from `/extension` into your Chrome Developer dashboard.

---

## 🔑 Why are there 2 Supabase URLs?
*   **SUPABASE_URL / KEY:** Used by the **AI Analyst** to quickly retrieve deep SEO principles using Vector Search (REST/RPC).
*   **SUPABASE_DB_URL:** Used by the **Setup Scripts** (psycopg2) to perform raw SQL migrations, schema updates, and manage user history with maximum stability.

## 💼 Professional Workflow
1. **Analyze:** Open the extension on any page and click "Analyze Content".
2. **Accept:** Click "Accept & Track" on suggestions you like.
3. **Train:** Click "Teach AI" to ingest the successful findings into the agent's long-term expertise.
4. **History:** Monitor your progress and scores in the History tab.

---
Built with ❤️ for SEO Professionals.
