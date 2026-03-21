import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import trafilatura
from services.knowledge_service import store_seo_knowledge

def train_from_url(url: str):
    """Scrapes a URL and stores the distilled SEO knowledge in the vector DB."""
    print(f"Reading and learning from: {url}...")
    
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        print("Failed to fetch the URL.")
        return
    
    # Extract clean text
    text = trafilatura.extract(downloaded)
    if not text:
        print("No readable content found.")
        return

    # We split large articles into chunks of ~500 words to keep vectors high-quality
    words = text.split()
    chunks = [" ".join(words[i:i+500]) for i in range(0, len(words), 500)]
    
    for i, chunk in enumerate(chunks):
        store_seo_knowledge(chunk, source=f"Trained from {url} (Part {i+1})")
        print(f"Chunk {i+1} memorized.")

    print(f"\n✅ Training complete! The agent now understands insights from {url}.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python train_agent.py [URL]")
    else:
        target_url = sys.argv[1]
        train_from_url(target_url)
