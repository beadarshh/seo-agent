from fastapi import APIRouter, BackgroundTasks, HTTPException
from models.schemas import ContentRequest, WritingAnalysisResponse, OptimizationCheckRequest, OptimizationCheckResponse
from services.writing_service import analyse_content_for_writing, check_content_optimization
from services.scheduler_service import manually_trigger_analysis
from db.database import get_supabase
import uuid
from datetime import datetime, timezone

router = APIRouter()

@router.post("/", response_model=WritingAnalysisResponse)
async def save_content(request: ContentRequest):
    supabase = get_supabase()
    
    # Save or update page
    existing = supabase.table("pages").select("*").eq("url", request.url).execute()
    
    # Meta description can be passed explicitly or taken from tags
    meta_desc = request.meta_description
    if not meta_desc and request.meta_tags:
        meta_desc = request.meta_tags.get("description") or request.meta_tags.get("og:description")

    page_data = {
        "url": request.url,
        "title": request.title,
        "meta_description": meta_desc,
        "content": request.content,
        "target_keyword": request.target_keyword,
        "headings": request.headings,
        "word_count": len(request.content.split()),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if existing.data:
        page_id = existing.data[0]["id"]
        supabase.table("pages").update(page_data).eq("id", page_id).execute()
    else:
        result = supabase.table("pages").insert(page_data).execute()
        page_id = result.data[0]["id"]
        
    analysis = await analyse_content_for_writing(
        page_id=page_id,
        title=request.title,
        meta=meta_desc,
        content=request.content,
        headings=request.headings,
        keyword=request.target_keyword,
        metadata={
            "meta_tags": request.meta_tags,
            "elements": request.elements,
            "images": request.images
        }
    )
    
    supabase.table("pages").update({"seo_score": analysis.seo_score}).eq("id", page_id).execute()
    return analysis

@router.post("/check_optimization", response_model=OptimizationCheckResponse)
async def check_optimization(request: OptimizationCheckRequest):
    result = await check_content_optimization(request.text)
    return result

@router.post("/{page_id}/publish")
async def publish_content(page_id: str):
    supabase = get_supabase()
    supabase.table("pages").update({
        "published_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", page_id).execute()
    return {"status": "success", "message": "Timer started for 14-day analysis."}

@router.post("/{page_id}/trigger-analysis")
async def trigger_analysis(page_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(manually_trigger_analysis, page_id)
    return {"status": "analysis_triggered"}
