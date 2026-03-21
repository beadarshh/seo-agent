import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.knowledge_service import store_seo_knowledge

deep_seo_principles = [
    "Always place the exact target keyword in the first 100 words of the body text. This gives search engines an immediate signal of topical relevance.",
    "Internal links should use descriptive, keyword-rich anchor text. Avoid generic 'click here' links as they pass no semantic context.",
    "The H1 tag must clearly state the page intent and include the primary keyword, but keep it natural. Only use a single H1 per page.",
    "LSI (Latent Semantic Indexing) keywords and synonyms should naturally complement the core topic. Using variation prevents keyword stuffing.",
    "Avoid thin content: ensure main topics answer user intent comprehensively. High-ranking pages typically cover WHO, WHAT, WHY, and HOW.",
    "Page titles should ideally be between 50-60 characters to prevent truncation in SERPs, and always start with the most important words.",
    "Meta descriptions don't directly impact rankings but heavily impact CTR. Write compelling 150-160 character summaries with a strong CTA.",
    "Headings structure (H1 > H2 > H3) must follow strict hierarchical order. Do not skip heading levels for styling purposes.",
    "Optimize for Zero-Click searches by explicitly formatting Q&A pairs. Use direct, definitive answers followed by bullet points if appropriate.",
    "Readability is a ranking factor by proxy through bounce rate. Keep sentences short, avoid excessive jargon, and break text into small paragraphs."
]

def seed():
    print("Seeding vector database with deep SEO principles...")
    for rule in deep_seo_principles:
        try:
            store_seo_knowledge(rule, source="Core Algorithm Rules")
            print(f"Stored: {rule[:30]}...")
        except Exception as e:
            print(f"Failed to store rule. Error: {e}")
            
if __name__ == "__main__":
    seed()
    print("Seeding complete.")
