from datetime import datetime, timedelta, timezone
from db.database import get_supabase
from services.twoweek_service import run_two_week_analysis
import asyncio

async def run_two_week_checks():
    """
    Runs daily at 9am.
    Finds all pages that:
    1. Have been published for exactly 14 days (within a 24hr window)
    2. Don't already have a completed 2-week report
    Then runs the full competitor + gap analysis for each.
    """
    supabase = get_supabase()
    now = datetime.now(timezone.utc)

    # Look for pages published between 14 and 15 days ago
    fourteen_days_ago = now - timedelta(days=14)
    fifteen_days_ago = now - timedelta(days=15)

    # Get pages in the 14-day window
    pages_result = supabase.table("pages").select("id, url, title, target_keyword, published_at") \
        .gte("published_at", fifteen_days_ago.isoformat()) \
        .lte("published_at", fourteen_days_ago.isoformat()) \
        .execute()

    if not pages_result.data:
        print(f"[{now}] No pages hit their 2-week mark today.")
        return

    for page in pages_result.data:
        page_id = page["id"]

        # Check if a report already exists for this page
        existing = supabase.table("two_week_reports") \
            .select("id") \
            .eq("page_id", page_id) \
            .eq("completed", True) \
            .execute()

        if existing.data:
            print(f"Report already exists for {page['url']}, skipping.")
            continue

        print(f"Triggering 2-week analysis for: {page['url']}")
        try:
            await run_two_week_analysis(page_id)
            # Throttle — wait 30s between pages to be respectful to Groq rate limits
            await asyncio.sleep(30)
        except Exception as e:
            print(f"Failed analysis for {page['url']}: {e}")

async def manually_trigger_analysis(page_id: str):
    """Allows manual trigger from the dashboard for testing."""
    await run_two_week_analysis(page_id)
