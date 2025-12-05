# ProduckAI Chrome Extension

## Installation

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select this directory (`apps/extension`)

## Usage

1. Navigate to a Jira ticket page (e.g., `https://your-domain.atlassian.net/browse/PROD-123`)
2. Click the ProduckAI extension icon in your toolbar
3. View related themes, scores, and customer quotes
4. Click "Copy PRD Outline" to generate a PRD template

## Development

The extension uses Manifest V3 and includes:
- `manifest.json`: Extension configuration
- `popup.html/js`: Popup UI when clicking extension icon
- `content.js`: Script injected into Jira pages
- `background.js`: Service worker for background tasks

## Note

Make sure the ProduckAI API is running at `http://localhost:8000` for the extension to work.
