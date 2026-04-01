(function() {
  // Check if listener is already added
  if (window.hasSeoAgentListener) return;
  window.hasSeoAgentListener = true;

  chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    if (request.action === "read_page") {
      try {
        const title = document.title || "";
        
        const metaTags = {};
        Array.from(document.getElementsByTagName('meta')).forEach(tag => {
          const name = tag.getAttribute('name') || tag.getAttribute('property');
          const content = tag.getAttribute('content');
          if (name && content) metaTags[name] = content;
        });

        const headings = {
          h1: Array.from(document.querySelectorAll('h1')).map(el => el.innerText.trim()).filter(t => t),
          h2: Array.from(document.querySelectorAll('h2')).map(el => el.innerText.trim()).filter(t => t),
          h3: Array.from(document.querySelectorAll('h3')).map(el => el.innerText.trim()).filter(t => t),
          h4: Array.from(document.querySelectorAll('h4')).map(el => el.innerText.trim()).filter(t => t),
        };

        const allTextElements = Array.from(document.querySelectorAll('p, li, span, h1, h2, h3, h4, h5, h6, blockquote, div, article, section, header, footer'))
                               .map(el => ({
                                 tag: el.tagName.toLowerCase(),
                                 text: el.innerText.trim(),
                                 length: el.innerText.trim().length
                               }))
                               .filter(item => item.length > 2); // Lower threshold to catch almost everything
        
        const fullContent = allTextElements.map(item => item.text).join("\n\n").substring(0, 50000); 
        const images = Array.from(document.querySelectorAll('img')).map(img => ({
          src: img.src,
          alt: img.alt || ""
        }));

        sendResponse({
          title: title,
          metaTags: metaTags,
          headings: headings,
          content: fullContent,
          elements: allTextElements,
          images: images,
          url: window.location.href
        });
      } catch (e) {
        sendResponse({ error: e.message });
      }
    }
  });
})();

