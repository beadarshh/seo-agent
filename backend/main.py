from fastapi import FastAPI
# trigger reload for .env change
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from routers import content, reports, dashboard, extension
from services.scheduler_service import run_two_week_checks
import uvicorn

app = FastAPI(title="SEO Writing Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(content.router, prefix="/api/content", tags=["content"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(extension.router, prefix="/api/extension", tags=["extension"])

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup():
    # Runs every day at 9am — checks which pages are now 14 days old
    scheduler.add_job(run_two_week_checks, "cron", hour=9, minute=0)
    scheduler.start()
    print("SEO Agent started. Scheduler running.")

@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()

@app.get("/")
async def root():
    return {"status": "SEO Agent is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
