from pydantic import BaseModel
from typing import List, Dict, Optional

class WritingSuggestion(BaseModel):
    id: Optional[str] = None
    suggestion_type: str
    priority: str
    current_value: str
    suggested_value: str
    reason: str

class WritingAnalysisResponse(BaseModel):
    page_id: str
    user_email: Optional[str] = None
    seo_score: int
    suggestions: List[WritingSuggestion]
    word_count: int
    keyword_density: float
    readability_score: float
    title_analysis: Dict
    meta_analysis: Dict
    heading_analysis: Dict

class ContentRequest(BaseModel):
    user_email: str
    url: str
    title: str
    meta_description: Optional[str] = None
    meta_tags: Optional[Dict] = None
    content: str
    target_keyword: Optional[str] = "seo"
    headings: Dict[str, List[str]]
    elements: Optional[List[Dict]] = None
    images: Optional[List[Dict]] = None

class OptimizationCheckRequest(BaseModel):
    text: str

class OptimizationCheckResponse(BaseModel):
    attention_score: int
    seo_score: int
    feedback: str
