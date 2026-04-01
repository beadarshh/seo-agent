from fastapi import APIRouter, HTTPException
from models.schemas import ContentRequest, WritingAnalysisResponse, WritingSuggestion
from services.writing_service import count_words, calculate_keyword_density, analyse_title, analyse_meta, analyse_headings, calculate_readability
from services.knowledge_service import retrieve_seo_knowledge, store_seo_knowledge
from groq import Groq
from config import settings
from db.database import get_supabase
from pydantic import BaseModel
import os, json, re

router = APIRouter()
client = Groq(api_key=settings.GROQ_API_KEY)

class TeachRequest(BaseModel):
    learned_rule: str
    source: str = "User Feedback"


@router.post("/teach", response_model=dict)
async def teach_ai_seo(request: TeachRequest):
    """Allows the extension to write new RAG memory rules base on feedback."""
    success = store_seo_knowledge(request.learned_rule, source=request.source)
    return {"status": "success", "message": "Rule recorded to deep pgvector memory.", "stored": success}

@router.post("/analyze", response_model=WritingAnalysisResponse)
async def analyze_extension_content(request: ContentRequest):
    """Called directly by the Chrome Extension."""
    supabase = get_supabase()
    
    # Take meta from tags if not explicit
    meta_desc = request.meta_description
    if not meta_desc and request.meta_tags:
        meta_desc = request.meta_tags.get("description") or request.meta_tags.get("og:description")

    # Upsert page
    page_data = {
        "user_email": request.user_email,
        "url": request.url,
        "title": request.title,
        "meta_description": meta_desc,
        "content": request.content,
        "target_keyword": request.target_keyword,
        "headings": request.headings,
        "updated_at": "now()"
    }
    
    try:
        page_res = supabase.table("pages").upsert(page_data, on_conflict="user_email, url").execute()
        if not page_res.data:
            # Maybe the constraint failed or table missing?
            raise HTTPException(status_code=500, detail="Failed to upsert page to Supabase.")
        page_id = page_res.data[0]["id"]
    except Exception as e:
        print(f"ERROR: Supabase Page Upsert Failed: {e}")
        # If it's a DNS error, we can't do much but report it clearly
        if "getaddrinfo failed" in str(e):
             raise HTTPException(status_code=503, detail="Database connection error. Please check your internet or Supabase URL.")
        raise HTTPException(status_code=500, detail=str(e))

    from services.writing_service import analyse_content_for_writing
    
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

    # Store suggestions in the database
    for sug in analysis.suggestions:
        try:
            supabase.table("suggestions").insert({
                "page_id": page_id,
                "type": sug.suggestion_type,
                "priority": sug.priority,
                "original_value": sug.current_value,
                "suggested_value": sug.suggested_value,
                "reason": sug.reason
            }).execute()
        except Exception as e:
            print(f"DEBUG: Failed to store suggestion result: {e}")

    # Update score
    supabase.table("pages").update({"seo_score": analysis.seo_score}).eq("id", page_id).execute()

    # Fill in response fields that might be missing from base analysis
    analysis.user_email = request.user_email
    return analysis

class AcceptRequest(BaseModel):
    suggestion_id: str

@router.post("/accept")
async def accept_suggestion(request: AcceptRequest):
    supabase = get_supabase()
    supabase.table("suggestions").update({
        "is_accepted": True,
        "accepted_at": "now()"
    }).eq("id", request.suggestion_id).execute()
    return {"status": "accepted"}

@router.get("/reports/{user_email}")
async def get_user_reports(user_email: str):
    supabase = get_supabase()
    # Fetch reports and join with page titles, filtering by user_email in the joined table
    res = supabase.table("two_week_reports").select("*, pages!inner(title, url, user_email)").eq("pages.user_email", user_email).execute()
    return res.data

@router.get("/history/{user_email}")
async def get_user_history(user_email: str):
    supabase = get_supabase()
    res = supabase.table("pages").select("id, title, url, seo_score, updated_at")\
        .eq("user_email", user_email).order("updated_at", desc=True).limit(30).execute()
    return res.data

@router.get("/page_suggestions/{page_id}")
async def get_page_suggestions(page_id: str):
    supabase = get_supabase()
    res = supabase.table("suggestions").select("*").eq("page_id", page_id).execute()
    return res.data
async def generate_user_report(user_email: str):
    supabase = get_supabase()
    # Get latest page to base report on
    latest = supabase.table("pages").select("id").eq("user_email", user_email).order("updated_at", desc=True).limit(1).execute()
    if not latest.data:
        raise HTTPException(status_code=400, detail="Please analyze some pages first before generating a gap report.")
    
    page_id = latest.data[0]["id"]
    # Create report entry
    res = supabase.table("two_week_reports").insert({
        "page_id": page_id,
        "overall_score": 75, # Base for now
        "gap_suggestions": ["Improve title relevance", "Add LSI keywords to H2s"]
    }).execute()
    return {"status": "success", "data": res.data}
