chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "analyze_content") {
    // Send to our local Python backend
    // Since Chrome blocks mixed content and CORS from standard websites, we use the background script
    const data = request.payload;

    // Use a placeholder keyword for now or extract from URL/Meta
    const keyword = promptUserForKeywordSnippet(data.url, data.title);

    console.log("DEBUG: Background sending fetch to:", "http://localhost:8000/api/extension/analyze");
    
    fetch('http://localhost:8000/api/extension/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_email: data.user_email,
        url: data.url,
        title: data.title,
        meta_description: data.meta_description,
        content: data.content,
        target_keyword: keyword,
        headings: data.headings
      })
    })
    .then(async response => {
       const text = await response.text();
       console.log("DEBUG: Raw Response Text:", text);
       try {
         return JSON.parse(text);
       } catch(e) {
         return { error: "API returned invalid JSON: " + text };
       }
    })
    .then(result => {
      sendResponse(result);
    })
    .catch(error => {
      console.error('DEBUG: Fetch Error:', error);
      sendResponse({ error: "Backend uncreachable. Status: " + error.message });
    });

    return true; // Keeps the sendResponse callback active for async
  }
});

function promptUserForKeywordSnippet(url, title) {
    // A simple heuristic for keyword if we don't ask the user explicitly
    // Just takes the most prominent words in the title, or ask user via popup (for MVP we guess)
    const words = title.split(' ').filter(w => w.length > 4);
    return words.slice(0, 2).join(' ') || "seo strategy"; 
}
