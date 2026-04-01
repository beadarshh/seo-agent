import re
import json
from groq import Groq
from config import settings
from models.schemas import WritingSuggestion, WritingAnalysisResponse
from typing import List, Dict, Any

client = Groq(api_key=settings.GROQ_API_KEY)

def count_words(text: str) -> int:
    return len(text.split())

def calculate_keyword_density(content: str, keyword: str) -> float:
    words = content.lower().split()
    total_words = len(words)
    if total_words == 0:
        return 0.0
    keyword_lower = keyword.lower()
    keyword_words = keyword_lower.split()
    count = 0
    if len(keyword_words) == 1:
        count = words.count(keyword_lower)
    else:
        content_lower = content.lower()
        count = content_lower.count(keyword_lower)
    return round((count / total_words) * 100, 2)

def analyse_title(title: str, keyword: str) -> Dict[str, Any]:
    issues = []
    score = 100
    length = len(title)

    if length < 30:
        issues.append("Title is too short (under 30 chars). Aim for 50-60.")
        score -= 20
    elif length > 60:
        issues.append(f"Title is {length} chars — will be cut off in Google at 60. Shorten it.")
        score -= 15

    if keyword.lower() not in title.lower():
        issues.append(f"Target keyword '{keyword}' is missing from the title.")
        score -= 30

    if not title[0].isupper():
        issues.append("Title should start with a capital letter.")
        score -= 5

    return {"length": length, "score": max(0, score), "issues": issues}

def analyse_meta(meta: str, keyword: str) -> Dict[str, Any]:
    issues = []
    score = 100
    if not meta:
        return {"length": 0, "score": 0, "issues": ["Meta description is missing — this is the text Google shows in search results."]}
    length = len(meta)
    if length < 120:
        issues.append(f"Meta description is {length} chars — too short. Aim for 150-160.")
        score -= 20
    elif length > 160:
        issues.append(f"Meta description is {length} chars — Google will truncate at 160.")
        score -= 10
    if keyword.lower() not in meta.lower():
        issues.append(f"Include the keyword '{keyword}' in the meta description.")
        score -= 25
    return {"length": length, "score": max(0, score), "issues": issues}

def analyse_headings(headings: Dict, keyword: str) -> Dict[str, Any]:
    issues = []
    score = 100
    h1s = headings.get("h1", [])
    h2s = headings.get("h2", [])

    if len(h1s) == 0:
        issues.append("No H1 found. Every page needs exactly one H1 tag.")
        score -= 30
    elif len(h1s) > 1:
        issues.append(f"You have {len(h1s)} H1 tags. Use only one — it confuses Google.")
        score -= 15

    if h1s and keyword.lower() not in " ".join(h1s).lower():
        issues.append(f"Put the keyword '{keyword}' in your H1 heading.")
        score -= 20

    if len(h2s) < 2:
        issues.append("Add more H2 subheadings to break up your content (aim for at least 3).")
        score -= 10

    return {"h1_count": len(h1s), "h2_count": len(h2s), "score": max(0, score), "issues": issues}

def calculate_readability(content: str) -> float:
    """Simplified Flesch Reading Ease approximation."""
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0.0
    words = content.split()
    if not words:
        return 0.0
    avg_sentence_length = len(words) / len(sentences)
    # Count syllables roughly
    syllables = sum(max(1, len(re.findall(r'[aeiouAEIOU]', word))) for word in words)
    avg_syllables = syllables / len(words)
    score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables)
    return round(max(0, min(100, score)), 1)

async def get_llm_writing_suggestions(
    title: str,
    meta: str,
    content: str,
    headings: Dict,
    keyword: str,
    word_count: int,
    keyword_density: float,
    metadata: Dict = None
) -> List[WritingSuggestion]:
    """Ask Groq for deep writing + SEO suggestions."""

    # Build a content summary to save tokens (Groq is fast but has limits)
    content_preview = content[:3000] + "..." if len(content) > 3000 else content
    headings_str = json.dumps(headings, indent=2)
    meta_tags_str = json.dumps(metadata.get("meta_tags", {}) if metadata else {}, indent=2)
    elements_summary = json.dumps(metadata.get("elements", [])[:20] if metadata else [], indent=2)

    prompt = f"""You are an expert SEO content editor. Analyse this content and give specific, actionable improvement suggestions.
You have access to the whole page metadata, including tags and elements.

CONTENT DETAILS:
- Title: {title}
- Meta description: {meta or "MISSING"}
- Meta Tags: {meta_tags_str}
- Target keyword: {keyword}
- Word count: {word_count}
- Keyword density: {keyword_density}%
- Headings: {headings_str}
- Elements (first 20): {elements_summary}
- Content preview: {content_preview}

SEO BENCHMARKS TO CHECK:
1. TITLE OPTIMIZATION: If the title is boring or weak, suggest a high-CTR, punchy rewrite with the keyword near the start.
2. H1/H2 HIERARCHY: Check if headings follow a logical structure and use descriptive subheadings.
3. PARAGRAPH BREVITY: If any paragraph > 60 words, suggest a specific split or rewrite.
4. SOCIAL & TECHNICAL TAG AUDIT: Audit OG/Twitter tags (OpenGraph), Robots tag, and Canonical tags from provided Meta Tags. If they are missing or have generic content, suggest specific improvements.
5. IMAGES & ALT TEXT: Suggest ALT tags for specific images found in elements. 
6. CTA & ENGAGEMENT: Is there an obvious "Next Step" or offer for the reader?
7. KEYWORD PROXIMITY: Is '{keyword}' used naturally in the first 100 words?

Return ONLY valid JSON array:
[
  {{
    "suggestion_type": "title|meta|heading|keyword_density|content_depth|readability|cta|para_length|tags|og_tags|images",
    "priority": "high|medium|low",
    "current_value": "...",
    "suggested_value": "...",
    "reason": "..."
  }}
]

Give 6-12 high-quality, actionable suggestions. ALWAYS suggest a better Title and Meta Description if the current ones aren't elite. Audit social tags for high-CTR sharing. Be extremely specific.
"""

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2500,
    )

    raw = response.choices[0].message.content.strip()
    
    # Robustly find the JSON array pattern
    json_match = re.search(r'\[\s*\{.*\}\s*\]', raw, re.DOTALL)
    if json_match:
        raw_json = json_match.group(0)
    else:
        # Fallback to previous cleaning
        raw_json = re.sub(r"```json\s*|\s*```", "", raw).strip()

    try:
        suggestions_data = json.loads(raw_json)
        if not isinstance(suggestions_data, list):
            suggestions_data = [suggestions_data]
        return [WritingSuggestion(**s) for s in suggestions_data if isinstance(s, dict)]
    except Exception as e:
        print(f"ERROR: LLM JSON Parse Failed: {e} | Raw: {raw[:500]}")
        return [WritingSuggestion(
            suggestion_type="System",
            priority="low",
            current_value="",
            suggested_value="",
            reason="The AI auditor provided an irregular response format. Please try one more time."
        )]

async def analyse_content_for_writing(
    page_id: str,
    title: str,
    meta: str,
    content: str,
    headings: Dict,
    keyword: str,
    metadata: Dict = None
) -> WritingAnalysisResponse:
    """Full writing analysis — called immediately when content is saved."""

    word_count = count_words(content)
    keyword_density = calculate_keyword_density(content, keyword)
    readability = calculate_readability(content)
    title_analysis = analyse_title(title, keyword)
    meta_analysis = analyse_meta(meta, keyword)
    heading_analysis = analyse_headings(headings, keyword)

    # Get LLM suggestions
    llm_suggestions = await get_llm_writing_suggestions(
        title, meta, content, headings, keyword, word_count, keyword_density, metadata
    )

    # Calculate overall SEO score
    seo_score = int(
        title_analysis["score"] * 0.25 +
        meta_analysis["score"] * 0.20 +
        heading_analysis["score"] * 0.20 +
        min(100, (readability / 100) * 100) * 0.15 +
        min(100, max(0, (keyword_density - 0.5) / 1.5 * 100)) * 0.20
    )

    return WritingAnalysisResponse(
        page_id=page_id,
        seo_score=min(100, seo_score),
        suggestions=llm_suggestions,
        word_count=word_count,
        keyword_density=keyword_density,
        readability_score=readability,
        title_analysis=title_analysis,
        meta_analysis=meta_analysis,
        heading_analysis=heading_analysis,
    )

async def check_content_optimization(text: str) -> Dict[str, Any]:
    """Compare 'Attention Grabber' vs 'SEO Optimized' quality of a snippet."""
    prompt = f"""Analyse this text snippet and score it on two scales (0-100):
1. **Attention Grabber**: Use of curiosity, strong verbs, emotional triggers, hooks.
2. **SEO Optimized**: Use of keywords naturally, clarity, relevance to search intent.

TEXT: "{text}"

Return ONLY valid JSON:
{{
  "attention_score": 00,
  "seo_score": 00,
  "feedback": "Why these scores? Short 2-sentence explanation."
}}
"""
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=500,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
    try:
        return json.loads(raw)
    except:
        return {
            "attention_score": 50,
            "seo_score": 50,
            "feedback": "Analysis failed to parse."
        }
