from db.database import get_supabase
from typing import List

# SKIPPED EMBEDDINGS FOR RENDER COMPATIBILITY (Rust not found)
# In production, use OpenAI or a cloud embedding API

def get_embedding(text: str) -> List[float]:
    """Generates a dummy vector since we removed fastembed for build compatibility."""
    return [0.0] * 384 # Placeholder

def retrieve_seo_knowledge(query: str, limit: int = 3) -> str:
    """Returns a simple list of SEO rules without using vector search (for now)."""
    # For a quick fix, just return some standard, fallback advice
    return "- Focus on high-intent keywords. - Keep title tags under 60 chars. - Ensure page speed is under 2s."

def store_seo_knowledge(content: str, source: str = "Learned Pattern"):
    """Stores the rule into Supabase (skipping the vector part)."""
    supabase = get_supabase()
    try:
        supabase.table("seo_knowledge").insert({
            "content": content,
            "source": source
        }).execute()
        return True
    except:
        return False
