// Listens for a message from the popup to extract data
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  if (request.action === "read_page") {
    // Extract basic SEO fields
    const title = document.title || "";
    
    // Meta description
    let metaDesc = "";
    const metaTag = document.querySelector('meta[name="description"]');
    if (metaTag) metaDesc = metaTag.getAttribute('content');

    // Headings
    const h1s = Array.from(document.querySelectorAll('h1')).map(el => el.innerText.trim());
    const h2s = Array.from(document.querySelectorAll('h2')).map(el => el.innerText.trim());

    // Main text content extraction
    // We include more structural tags and increase character limit
    const paragraphs = Array.from(document.querySelectorAll('p, li, span, h2, h3, h4, blockquote, div.main, article'))
                           .map(el => el.innerText.trim())
                           .filter(text => text.length > 15);
    
    let fullContent = paragraphs.join("\n");
    if (fullContent.length > 10000) fullContent = fullContent.substring(0, 10000); 

    sendResponse({
      title: title,
      metaDesc: metaDesc,
      headings: {
        h1: h1s,
        h2: h2s
      },
      content: fullContent
    });
  }
});
