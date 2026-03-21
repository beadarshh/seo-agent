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
    keyword_density: float
) -> List[WritingSuggestion]:
    """Ask Groq for deep writing + SEO suggestions."""

    # Build a content summary to save tokens (Groq is fast but has limits)
    content_preview = content[:2000] + "..." if len(content) > 2000 else content
    headings_str = json.dumps(headings, indent=2)

    prompt = f"""You are an expert SEO content editor. Analyse this content and give specific, actionable improvement suggestions.

CONTENT DETAILS:
- Title: {title}
- Meta description: {meta or "MISSING"}
- Target keyword: {keyword}
- Word count: {word_count}
- Keyword density: {keyword_density}%
- Headings: {headings_str}
- Content preview: {content_preview}

SEO BENCHMARKS TO CHECK:
1. Keyword in first 100 words of content?
2. Is keyword density between 1-2%? (under = weak, over = stuffing)
3. Are H2s descriptive and keyword-related?
4. Does the content cover the topic comprehensively?
5. Are there any missing semantic/LSI keywords for '{keyword}'?
6. Is there a clear call-to-action?
7. Sentence length variety (mix short and long)?

Return ONLY valid JSON array (no markdown, no explanation outside JSON):
[
  {{
    "suggestion_type": "title|meta|heading|keyword_density|content_depth|readability|cta",
    "priority": "high|medium|low",
    "current_value": "what is currently there",
    "suggested_value": "specific improved version",
    "reason": "why this change will help SEO in plain English"
  }}
]

Give 3-7 suggestions. Focus on HIGH priority items first. Be specific — suggest actual rewritten titles/sentences, not vague advice."""

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000,
    )

    raw = response.choices[0].message.content.strip()

    # Clean up if model adds markdown fences
    raw = re.sub(r"```json\s*|\s*```", "", raw).strip()

    try:
        suggestions_data = json.loads(raw)
        return [WritingSuggestion(**s) for s in suggestions_data]
    except json.JSONDecodeError:
        # Fallback if LLM returns something unexpected
        return [WritingSuggestion(
            suggestion_type="content_depth",
            priority="medium",
            current_value="",
            suggested_value="",
            reason="LLM analysis unavailable — check your Groq API key."
        )]

async def analyse_content_for_writing(
    page_id: str,
    title: str,
    meta: str,
    content: str,
    headings: Dict,
    keyword: str
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
        title, meta, content, headings, keyword, word_count, keyword_density
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
