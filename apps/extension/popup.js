// ProduckAI Popup Script
const API_URL = 'http://localhost:8000';

async function loadTicketData() {
  const contentDiv = document.getElementById('content');

  try {
    // Get current tab URL
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = tab.url;

    // Extract Jira ticket key from URL
    const match = url.match(/browse\/([A-Z]+-\d+)/);
    if (!match) {
      contentDiv.innerHTML = '<p>Not a Jira ticket page.</p>';
      return;
    }

    const ticketKey = match[1];

    // Fetch ticket score from API
    const response = await fetch(`${API_URL}/tickets/${ticketKey}/score`);
    const data = await response.json();

    // Render data
    let html = `<h2>${ticketKey}</h2>`;

    if (data.themes.length === 0) {
      html += '<p>No themes found for this ticket.</p>';
    } else {
      html += `<p><strong>Overall Score:</strong> ${data.overall_score.toFixed(2)}</p>`;

      html += '<h3>Related Themes:</h3>';
      data.themes.forEach(theme => {
        html += `
          <div class="theme">
            <div class="theme-label">${theme.label}</div>
            <div class="theme-score">Score: ${theme.score.toFixed(2)} | Coverage: ${(theme.coverage * 100).toFixed(0)}%</div>
          </div>
        `;
      });

      if (data.top_quotes.length > 0) {
        html += '<h3>Top Customer Quotes:</h3>';
        data.top_quotes.forEach(quote => {
          html += `
            <div class="quote">
              "${quote.text}"
              <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">
                ${quote.source} - ${new Date(quote.created_at).toLocaleDateString()}
              </div>
            </div>
          `;
        });
      }

      html += '<button onclick="copyPRD()">Copy PRD Outline</button>';
    }

    contentDiv.innerHTML = html;
  } catch (error) {
    console.error('Error loading ticket data:', error);
    contentDiv.innerHTML = '<p>Error loading data. Make sure the API is running.</p>';
  }
}

async function copyPRD() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = tab.url;
    const match = url.match(/browse\/([A-Z]+-\d+)/);
    const ticketKey = match[1];

    const response = await fetch(`${API_URL}/tickets/${ticketKey}/draft_prd`, {
      method: 'POST',
    });
    const data = await response.json();

    await navigator.clipboard.writeText(data.prd_markdown);
    alert('PRD outline copied to clipboard!');
  } catch (error) {
    console.error('Error copying PRD:', error);
    alert('Failed to copy PRD outline.');
  }
}

// Load data when popup opens
document.addEventListener('DOMContentLoaded', loadTicketData);
