from fastapi import APIRouter
from models.schemas import ContentRequest, WritingAnalysisResponse, WritingSuggestion
from services.writing_service import count_words, calculate_keyword_density, analyse_title, analyse_meta, analyse_headings, calculate_readability
from services.knowledge_service import retrieve_seo_knowledge, store_seo_knowledge
from groq import Groq
from config import settings
from db.database import get_supabase
from pydantic import BaseModel
import json, re

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
    
    # Upsert page
    page_data = {
        "user_email": request.user_email,
        "url": request.url,
        "title": request.title,
        "meta_description": request.meta_description,
        "content": request.content,
        "target_keyword": request.target_keyword,
        "headings": request.headings,
        "updated_at": "now()"
    }
    
    page_res = supabase.table("pages").upsert(page_data, on_conflict="user_email, url").execute()
    page_id = page_res.data[0]["id"]

    word_count = count_words(request.content)
    keyword_density = calculate_keyword_density(request.content, request.target_keyword)
    rag_context = retrieve_seo_knowledge(f"SEO best practices for {request.target_keyword}")

    headings_str = json.dumps(request.headings, indent=2)
    # Increase preview to 4000 chars for more context
    content_preview = request.content[:4000] + "..." if len(request.content) > 4000 else request.content

    system_prompt = f"""You are an elite SEO auditor. 
    Memory: {rag_context if rag_context else "Standard elite knowledge."}
    Context: {request.url} | {request.title} | {request.target_keyword}
    Density: {keyword_density}%
    Content: {content_preview}

    Identify structural, technical or tactical SEO gaps.
    IMPORTANT: For each suggestion, provide the EXACT rewritten text if it's a content/title/heading change.
    Make the suggested_value a catchy, SEO-optimized version of the current_value.
    Return ONLY a valid JSON array of 3-5 high quality suggestions.
    FORMAT:
    [
      {{
        "suggestion_type": "...",
        "priority": "high|medium|low",
        "current_value": "...",
        "suggested_value": "...",
        "reason": "..."
      }}
    ]"""

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": system_prompt}],
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()
    print(f"DEBUG: Raw LLM Output: {raw}")

    json_match = re.search(r'\[\s*\{.*\}\s*\]', raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)
    else:
        raw = re.sub(r"```json\s*|\s*```", "", raw).strip()

    llm_suggestions = []
    try:
        suggestions_data = json.loads(raw)
        if not isinstance(suggestions_data, list):
            suggestions_data = [suggestions_data]
            
        for s in suggestions_data:
            try:
                s_type = s.get("suggestion_type", s.get("type", "Content"))
                s_priority = s.get("priority", "medium")
                s_orig = s.get("current_value", s.get("original_value", ""))
                s_sug = s.get("suggested_value", s.get("suggestion", ""))
                s_reason = s.get("reason", "")
                
                s_res = supabase.table("suggestions").insert({
                    "page_id": page_id,
                    "type": s_type,
                    "priority": s_priority,
                    "original_value": s_orig,
                    "suggested_value": s_sug,
                    "reason": s_reason
                }).execute()
                
                sug_id = s_res.data[0]["id"]
                llm_suggestions.append(WritingSuggestion(
                    id=sug_id,
                    suggestion_type=s_type,
                    priority=s_priority,
                    current_value=s_orig,
                    suggested_value=s_sug,
                    reason=s_reason
                ))
            except Exception as se:
                print(f"DEBUG: Failed to store suggestion: {se}")
    except Exception as e:
        print(f"DEBUG: JSON Parse Error: {e}")

    if not llm_suggestions:
        llm_suggestions.append(WritingSuggestion(
            id="error-fallback",
            suggestion_type="System",
            priority="low",
            current_value="N/A",
            suggested_value="N/A",
            reason="The AI analyst encountered an issue parsing the feedback. Please try analyzing again in a moment."
        ))

    penalty = sum(20 for s in llm_suggestions if s.priority == 'high') + sum(10 for s in llm_suggestions if s.priority == 'medium')
    seo_score = max(0, 100 - penalty)
    
    supabase.table("pages").update({"seo_score": seo_score}).eq("id", page_id).execute()

    return WritingAnalysisResponse(
        page_id=page_id,
        user_email=request.user_email,
        seo_score=seo_score,
        suggestions=llm_suggestions,
        word_count=word_count,
        keyword_density=keyword_density,
        readability_score=calculate_readability(request.content),
        title_analysis=analyse_title(request.title, request.target_keyword),
        meta_analysis=analyse_meta(request.meta_description, request.target_keyword),
        heading_analysis=analyse_headings(request.headings, request.target_keyword)
    )

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
