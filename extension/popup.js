document.addEventListener('DOMContentLoaded', async () => {
    chrome.storage.local.get(['userEmail'], (result) => {
        if (result.userEmail) {
            showApp(result.userEmail);
        } else {
            showLogin();
        }
    });

    initTabs();
    initSearch();
});

let currentAnalysisData = null; // Store for "Teach AI"

function showLogin() {
    document.getElementById('login-screen').classList.remove('hidden');
    document.getElementById('app-ui').classList.add('hidden');
}

async function showApp(email) {
    document.getElementById('login-screen').classList.add('hidden');
    document.getElementById('app-ui').classList.remove('hidden');
    document.getElementById('global-search').placeholder = email;

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
        document.getElementById('page-title').innerText = tab.title || "Unknown Page";
        document.getElementById('page-url').innerText = tab.url ? new URL(tab.url).hostname : "local";
    }
}

function initTabs() {
    const links = document.querySelectorAll('.tab-link');
    links.forEach(link => {
        link.addEventListener('click', async () => {
            const tabId = link.getAttribute('data-tab');
            links.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
            document.getElementById(tabId).classList.remove('hidden');

            const { userEmail } = await chrome.storage.local.get(['userEmail']);
            if (tabId === 'history-tab') loadHistory(userEmail);
            if (tabId === 'suggestions-tab') loadReports(userEmail);
        });
    });
}

function initSearch() {
    const searchInput = document.getElementById('global-search');
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        document.querySelectorAll('.history-item, .suggestion-item').forEach(item => {
            const text = item.innerText.toLowerCase();
            item.style.display = text.includes(query) ? (item.classList.contains('history-item') ? 'flex' : 'block') : 'none';
        });
    });
}

async function loadHistory(email) {
    const list = document.getElementById('history-list');
    list.innerHTML = `<p class="empty-msg">Loading history...</p>`;
    try {
        const res = await fetch(`http://localhost:8000/api/extension/history/${email}`);
        const data = await res.json();
        list.innerHTML = "";
        if (!data || data.length === 0) {
            list.innerHTML = `<p class="empty-msg">No history found.</p>`;
            return;
        }
        data.forEach(item => {
            const div = document.createElement('div');
            div.className = 'history-item clickable';
            div.innerHTML = `
                <div class="history-info">
                    <h4>${item.title || "Untitled"}</h4>
                    <p>${new URL(item.url).hostname} • ${new Date(item.updated_at).toLocaleDateString()}</p>
                </div>
                <div class="history-score">${item.seo_score}%</div>
            `;
            div.addEventListener('click', () => viewHistoryDetails(item));
            list.appendChild(div);
        });
    } catch(e) {
        list.innerHTML = `<p class="empty-msg">Error loading history.</p>`;
    }
}

async function viewHistoryDetails(item) {
    document.querySelector('[data-tab="agent-tab"]').click();
    document.getElementById('initial-state').classList.add('hidden');
    document.getElementById('results-area').classList.remove('hidden');
    document.getElementById('score-display').innerText = item.seo_score + "%";
    
    const list = document.getElementById('suggestions-list');
    list.innerHTML = `<p class="empty-msg">Retrieving recommendations...</p>`;

    try {
        const res = await fetch(`http://localhost:8000/api/extension/page_suggestions/${item.id}`);
        const data = await res.json();
        currentAnalysisData = { suggestions: data }; // Set for teaching
        renderSuggestions(data);
    } catch(e) {
        list.innerHTML = `<p class="empty-msg">Failed to load archived suggestions.</p>`;
    }
}

function renderSuggestions(suggestions) {
    const list = document.getElementById('suggestions-list');
    list.innerHTML = "";
    if(!suggestions || suggestions.length === 0) {
        list.innerHTML = `<p class="empty-msg">No suggestions recorded.</p>`;
        return;
    }
    suggestions.forEach(sug => {
        const div = document.createElement('div');
        div.className = `suggestion-item`;
        div.innerHTML = `
          <div class="suggestion-header">
             <h4>${(sug.suggestion_type || sug.type).replace('_', ' ')}</h4>
             <span class="priority-tag">${sug.priority}</span>
          </div>
          <p class="reason-text">${sug.reason}</p>
          ${sug.suggested_value ? `
              <div class="rewrite-box">
                <span class="rewrite-label">Rewrite To:</span>
                <div class="rewrite-text">${sug.suggested_value}</div>
              </div>
          ` : ''}
          <button class="accept-btn" data-id="${sug.id}" ${sug.is_accepted ? 'disabled' : ''}>
            ${sug.is_accepted ? 'Accepted ✅' : 'Accept & Track'}
          </button>
        `;
        list.appendChild(div);
    });
    attachAcceptListeners();
}

function attachAcceptListeners() {
    document.querySelectorAll('.accept-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const sid = e.target.getAttribute('data-id');
            e.target.innerText = "Accepted ✅";
            e.target.disabled = true;
            fetch('http://localhost:8000/api/extension/accept', {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ suggestion_id: sid })
            });
        });
    });
}

async function loadReports(email) {
    const list = document.getElementById('reports-list');
    list.innerHTML = `<p class="empty-msg">Loading reports...</p>`;
    try {
        const res = await fetch(`http://localhost:8000/api/extension/reports/${email}`);
        const data = await res.json();
        list.innerHTML = "";
        if (!data || data.length === 0) {
            list.innerHTML = `<p class="empty-msg">No 2-week reports available yet.</p>`;
            return;
        }
        data.forEach(report => {
            const div = document.createElement('div');
            div.className = 'history-item';
            div.innerHTML = `
                <div class="history-info">
                    <h4>${report.pages?.title || "Page Report"}</h4>
                    <p>Status: ${report.status} • Updated: ${new Date(report.created_at).toLocaleDateString()}</p>
                </div>
                <div class="history-score">${report.new_score || '--'}</div>
            `;
            list.appendChild(div);
        });
    } catch(e) {
        list.innerHTML = `<p class="empty-msg">Error loading reports.</p>`;
    }
}

document.getElementById('login-btn').addEventListener('click', () => {
    const email = document.getElementById('user-email-input').value;
    if (email && email.includes('@')) {
        chrome.storage.local.set({ userEmail: email }, () => {
            showApp(email);
        });
    }
});

document.getElementById('logout-btn').addEventListener('click', () => {
    chrome.storage.local.remove(['userEmail'], () => {
        showLogin();
    });
});

document.getElementById('analyze-btn').addEventListener('click', async () => {
  const loader = document.getElementById('loader');
  const resultsArea = document.getElementById('results-area');
  const initialState = document.getElementById('initial-state');
  
  initialState.classList.add('hidden');
  loader.classList.remove('hidden');
  document.getElementById('suggestions-list').innerHTML = "";

  const { userEmail } = await chrome.storage.local.get(['userEmail']);
  let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    files: ['content.js']
  }, () => {
    chrome.tabs.sendMessage(tab.id, { action: "read_page" }, (response) => {
      chrome.runtime.sendMessage({
        action: "analyze_content",
        payload: {
          user_email: userEmail,
          url: tab.url,
          title: response.title,
          meta_description: response.metaDesc,
          content: response.content,
          headings: response.headings
        }
      }, (apiResponse) => {
        loader.classList.add('hidden');
        if (!apiResponse || apiResponse.error) {
          alert("Error: " + (apiResponse?.error || "Invalid response"));
          initialState.classList.remove('hidden');
          return;
        }
        resultsArea.classList.remove('hidden');
        document.getElementById('score-display').innerText = (apiResponse.seo_score || 0) + "%";
        currentAnalysisData = apiResponse; // Save for Teach AI
        renderSuggestions(apiResponse.suggestions);
      });
    });
  });
});

document.getElementById('learn-btn').addEventListener('click', () => {
  if(!currentAnalysisData || !currentAnalysisData.suggestions) {
      alert("No data to ingest yet. Analyze a page first!");
      return;
  }
  
  const highPriority = currentAnalysisData.suggestions
    .filter(s => s.priority === 'high' || s.priority === 'medium')
    .map(s => `${s.suggestion_type}: ${s.reason}`)
    .join(". ");

  if(!highPriority) {
      alert("Page is already highly optimized. Data ingested.");
      return;
  }

  fetch('http://localhost:8000/api/extension/teach', {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ learned_rule: `Optimizing for: ${highPriority}`, source: "Auto-Ingestion" })
  }).then(() => {
      const btn = document.getElementById('learn-btn');
      btn.outerHTML = `
        <div class="ingested-status">
          <svg class="check-icon" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          <div class="status-content">
            <strong>Knowledge Ingested</strong>
            <span>Training AI with these SEO patterns...</span>
          </div>
        </div>`;
  });
});
