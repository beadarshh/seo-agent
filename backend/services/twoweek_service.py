import json
import re
from groq import Groq
from config import settings
from services.scraper_service import scrape_competitors
from db.database import get_supabase
from typing import List, Dict, Any
from datetime import datetime

client = Groq(api_key=settings.GROQ_API_KEY)

async def run_gap_analysis(
    our_page: Dict,
    competitors: List[Dict],
    keyword: str
) -> Dict[str, Any]:
    """Use Groq to compare our page against top competitors and find gaps."""

    if not competitors:
        return {"gaps": [], "strengths": [], "overall_assessment": "No competitors found to compare against."}

    # Build a concise competitor summary to stay within token limits
    comp_summary = []
    for i, comp in enumerate(competitors[:3], 1):
        comp_summary.append(f"""
Competitor {i}: {comp['url']}
- Title: {comp['title']}
- Word count: {comp['word_count']}
- H2 headings: {', '.join(comp['headings'].get('h2', [])[:5])}
- Content preview: {comp['content'][:800]}
""")

    our_summary = f"""
OUR PAGE: {our_page['url']}
- Title: {our_page['title']}
- Word count: {our_page.get('word_count', 0)}
- H2 headings: {', '.join(our_page.get('headings', {}).get('h2', [])[:5])}
- Content preview: {our_page.get('content', '')[:1000]}
"""

    prompt = f"""You are an expert SEO strategist. Compare our page against the top-ranking competitors for the keyword "{keyword}".

{our_summary}

TOP COMPETITORS:
{"".join(comp_summary)}

Analyse:
1. What topics/subtopics do competitors cover that we don't?
2. What questions are competitors answering that we miss?
3. Where are competitors weaker (our strengths)?
4. What structural differences exist (word count, heading depth)?
5. What specific sections should we ADD to our content?

Return ONLY valid JSON (no markdown):
{{
  "gaps": [
    {{
      "priority": "high|medium|low",
      "gap_type": "missing_topic|thin_coverage|missing_section|word_count|missing_faq",
      "description": "specific gap",
      "suggested_fix": "exactly what to add/change",
      "competitor_example": "which competitor does this well"
    }}
  ],
  "strengths": ["what we do better than competitors"],
  "word_count_gap": {{"ours": 0, "competitor_avg": 0, "recommendation": ""}},
  "overall_assessment": "2-3 sentence summary of competitive position"
}}"""

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2500,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"```json\s*|\s*```", "", raw).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "gaps": [],
            "strengths": [],
            "overall_assessment": "Analysis parsing failed. Raw response saved for debugging.",
            "raw": raw
        }

async def run_two_week_analysis(page_id: str) -> bool:
    """Full two-week analysis: scrape competitors, run gap analysis, save report."""
    supabase = get_supabase()

    # Fetch the page
    result = supabase.table("pages").select("*").eq("id", page_id).execute()
    if not result.data:
        print(f"Page {page_id} not found")
        return False

    page = result.data[0]
    keyword = page["target_keyword"]
    page_url = page["url"]

    print(f"Starting 2-week analysis for: {page_url} (keyword: {keyword})")

    # Scrape competitors
    competitors = await scrape_competitors(keyword, page_url)
    print(f"Scraped {len(competitors)} competitor pages")

    # Prepare our page data
    our_page = {
        "url": page_url,
        "title": page["title"],
        "content": page["content"],
        "headings": page["headings"] or {},
        "word_count": page["word_count"] or 0,
    }

    # Run gap analysis
    gap_analysis = await run_gap_analysis(our_page, competitors, keyword)

    # Format gap suggestions for storage
    gap_suggestions = []
    for gap in gap_analysis.get("gaps", []):
        gap_suggestions.append({
            "priority": gap.get("priority", "medium"),
            "type": gap.get("gap_type", "general"),
            "description": gap.get("description", ""),
            "suggested_fix": gap.get("suggested_fix", ""),
            "competitor_example": gap.get("competitor_example", "")
        })

    # Calculate score (simple: 100 - penalty for each high/medium gap)
    high_gaps = sum(1 for g in gap_suggestions if g["priority"] == "high")
    medium_gaps = sum(1 for g in gap_suggestions if g["priority"] == "medium")
    overall_score = max(0, 100 - (high_gaps * 15) - (medium_gaps * 7))

    # Save the report
    supabase.table("two_week_reports").insert({
        "page_id": page_id,
        "competitor_urls": [c["url"] for c in competitors],
        "competitor_analysis": {
            "strengths": gap_analysis.get("strengths", []),
            "word_count_gap": gap_analysis.get("word_count_gap", {}),
            "overall_assessment": gap_analysis.get("overall_assessment", ""),
            "competitors_scraped": len(competitors)
        },
        "gap_suggestions": gap_suggestions,
        "overall_score": overall_score,
        "completed": True
    }).execute()

    print(f"2-week report saved for {page_url}. Score: {overall_score}")
    return True
