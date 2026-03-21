import trafilatura
from bs4 import BeautifulSoup
from googlesearch import search
from typing import List, Dict

async def scrape_competitors(keyword: str, our_url: str) -> List[Dict]:
    results = []
    # Get top 5 google results
    try:
        urls = list(search(keyword, num_results=5, lang="en"))
    except Exception as e:
        print(f"Error searching google: {e}")
        return results

    for url in urls:
        if url == our_url or our_url in url:
            continue
            
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(downloaded)
                soup = BeautifulSoup(downloaded, 'html.parser')
                title = soup.title.string if soup.title else ""
                h2s = [h2.get_text(strip=True) for h2 in soup.find_all('h2')]
                
                if text:
                    results.append({
                        "url": url,
                        "title": title,
                        "content": text,
                        "word_count": len(text.split()),
                        "headings": {"h2": h2s}
                    })
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            
    return results[:3] # Returning top 3 as expected by the twoweek_service
