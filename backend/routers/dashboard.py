from fastapi import APIRouter
from db.database import get_supabase

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats():
    supabase = get_supabase()
    pages = supabase.table("pages").select("id", count="exact").execute()
    reports = supabase.table("two_week_reports").select("id", count="exact").execute()
    return {
        "total_pages_tracked": pages.count if hasattr(pages, 'count') else len(pages.data),
        "total_reports_generated": reports.count if hasattr(reports, 'count') else len(reports.data),
        "status": "Healthy"
    }
