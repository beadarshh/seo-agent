from fastapi import APIRouter
from db.database import get_supabase

router = APIRouter()

@router.get("/")
async def get_all_reports():
    supabase = get_supabase()
    reports = supabase.table("two_week_reports").select("*, pages(url, target_keyword)").order("created_at", desc=True).execute()
    return reports.data

@router.get("/{report_id}")
async def get_report(report_id: str):
    supabase = get_supabase()
    report = supabase.table("two_week_reports").select("*, pages(url, target_keyword, content)").eq("id", report_id).execute()
    if not report.data:
        return {"error": "Report not found"}
    return report.data[0]
