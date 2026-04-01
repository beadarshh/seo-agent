document.addEventListener('DOMContentLoaded', async () => {
    chrome.storage.local.get(['userEmail'], (result) => {
        if (result.userEmail) {
            showApp(result.userEmail);
        } else {
            showLogin();
        }
    });

    document.getElementById('generate-gap-btn').addEventListener('click', async () => {
        const { userEmail } = await chrome.storage.local.get(['userEmail']);
        const btn = document.getElementById('generate-gap-btn');
        btn.disabled = true;
        btn.innerText = "Processing Data...";
        try {
            await fetch(`https://seo-writing-agent.onrender.com/api/extension/generate_report/${userEmail}`, { method: 'POST' });
            loadGapAnalysis(userEmail);
        } catch (e) {
            alert("Audit generation failed. Database might be busy.");
        } finally {
            btn.disabled = false;
            btn.innerText = "Generate New Analysis";
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
            if (tabId === 'gap-tab') loadGapAnalysis(userEmail);
            if (tabId === 'deep-check-tab') document.getElementById('deep-check-input').value = "";
        });
    });
}

async function loadGapAnalysis(email) {
    const list = document.getElementById('gap-list');
    list.innerHTML = `<p class="empty-msg">Analyzing gaps...</p>`;
    try {
        const res = await fetch(`https://seo-writing-agent.onrender.com/api/extension/reports/${email}`);
        const data = await res.json();
        list.innerHTML = "";
        if (!data || data.length === 0) {
            list.innerHTML = `<p class="empty-msg">No bi-weekly reports yet. Analyze more pages!</p>`;
            return;
        }
        data.forEach(item => {
            const div = document.createElement('div');
            div.className = 'history-item clickable';
            div.innerHTML = `
                <div class="history-info">
                    <h4>${item.pages?.title || "Untitled Report"}</h4>
                    <p>Gap Analysis • ${new Date(item.created_at).toLocaleDateString()}</p>
                </div>
                <div class="history-score">${item.overall_score || '--'}</div>
            `;
            list.appendChild(div);
        });
    } catch (e) {
        list.innerHTML = `<p class="empty-msg">Gap analysis temporarily unavailable.</p>`;
    }
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
        const res = await fetch(`https://seo-writing-agent.onrender.com/api/extension/history/${email}`);
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
    } catch (e) {
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
        const res = await fetch(`https://seo-writing-agent.onrender.com/api/extension/page_suggestions/${item.id}`);
        const data = await res.json();
        currentAnalysisData = { suggestions: data }; // Set for teaching
        renderSuggestions(data);
    } catch (e) {
        list.innerHTML = `<p class="empty-msg">Failed to load archived suggestions.</p>`;
    }
}

function renderSuggestions(suggestions) {
    const list = document.getElementById('suggestions-list');
    list.innerHTML = "";
    if (!suggestions || suggestions.length === 0) {
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
            fetch('https://seo-writing-agent.onrender.com/api/extension/accept', {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ suggestion_id: sid })
            });
        });
    });
}

document.getElementById('login-btn').addEventListener('click', () => {
    const email = document.getElementById('user-email-input').value;
    if (email && email.includes('@')) {
        chrome.storage.local.set({ userEmail: email }, () => {
            showApp(email);
        });
    } else {
        alert("Please enter a valid email.");
    }
});

document.getElementById('logout-btn').addEventListener('click', () => {
    chrome.storage.local.remove(['userEmail', 'userPasscode'], () => {
        showLogin();
    });
});

document.getElementById('check-text-btn').addEventListener('click', async () => {
    const text = document.getElementById('deep-check-input').value;
    if (!text || text.trim().length < 5) {
        alert("Please enter some text to analyze.");
        return;
    }

    const btn = document.getElementById('check-text-btn');
    const results = document.getElementById('deep-check-results');
    btn.disabled = true;
    btn.innerText = "Analyzing Content...";

    try {
        const response = await fetch('https://seo-writing-agent.onrender.com/api/content/check_optimization', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        const data = await response.json();

        results.classList.remove('hidden');
        document.getElementById('attention-bar').style.width = `${data.attention_score}%`;
        document.getElementById('seo-bar').style.width = `${data.seo_score}%`;
        document.getElementById('deep-check-feedback').innerText = data.feedback;
    } catch (e) {
        alert("Optimization check failed. Is the backend running?");
    } finally {
        btn.disabled = false;
        btn.innerText = "Analyze Optimization";
    }
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
            if (!response || response.error) {
                loader.classList.add('hidden');
                initialState.classList.remove('hidden');
                alert("Failed to read page content. Please refresh the page and try again.");
                return;
            }
            chrome.runtime.sendMessage({
                action: "analyze_content",
                payload: {
                    user_email: userEmail,
                    url: tab.url,
                    title: response.title || tab.title,
                    meta_tags: response.metaTags,
                    content: response.content || "",
                    headings: response.headings || {},
                    elements: response.elements || [],
                    images: response.images || []
                }
            }, (apiResponse) => {
                loader.classList.add('hidden');
                if (!apiResponse || apiResponse.error) {
                    alert("Error: " + (apiResponse?.error || "Invalid response from background"));
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
    if (!currentAnalysisData || !currentAnalysisData.suggestions) {
        alert("No data to ingest yet. Analyze a page first!");
        return;
    }

    const highPriority = currentAnalysisData.suggestions
        .filter(s => s.priority === 'high' || s.priority === 'medium')
        .map(s => `${s.suggestion_type}: ${s.reason}`)
        .join(". ");

    if (!highPriority) {
        alert("Page is already highly optimized. Data ingested.");
        return;
    }

    fetch('https://seo-writing-agent.onrender.com/api/extension/teach', {
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
