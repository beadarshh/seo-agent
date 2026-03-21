from fastembed import TextEmbedding
from db.database import get_supabase
from typing import List

# Load embedding model locally (lightweight, ~100MB model downloaded on first run)
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

def get_embedding(text: str) -> List[float]:
    """Generates a 384-dimensional vector for a string."""
    embeddings = list(embedding_model.embed([text]))
    return embeddings[0].tolist()

def retrieve_seo_knowledge(query: str, limit: int = 3) -> str:
    """Finds deep SEO principles related to the user's query/context."""
    supabase = get_supabase()
    query_vector = get_embedding(query)
    
    # Needs Postgres function match_seo_knowledge
    result = supabase.rpc(
        "match_seo_knowledge",
        {
            "query_embedding": query_vector,
            "match_threshold": 0.5,
            "match_count": limit
        }
    ).execute()

    if not result.data:
        return ""

    context = "\n".join([f"- {item['content']} (Source: {item['source']})" for item in result.data])
    return context

def store_seo_knowledge(content: str, source: str = "Learned Pattern"):
    """Stores a new SEO principle into the vector database."""
    supabase = get_supabase()
    vector = get_embedding(content)
    
    supabase.table("seo_knowledge").insert({
        "content": content,
        "embedding": vector,
        "source": source
    }).execute()
    return True
