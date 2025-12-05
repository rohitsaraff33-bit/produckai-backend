# Pre-Release Testing Guide

**Purpose:** Test ProduckAI MCP Server before PyPI publication and GitHub launch.

**Status:** Pre-Release (Package not yet on PyPI)

---

## Prerequisites

Before you begin testing:

- ✅ Python 3.11+ installed
- ✅ Claude Desktop installed
- ✅ Anthropic API Key available
- ✅ Terminal/command line access
- ✅ **ProduckAI Backend running** (see Part 0 below)

**Optional for integration testing:**
- Slack workspace admin access
- Google Cloud project access
- JIRA account with admin rights
- Zoom account with recording access

**⚠️  IMPORTANT:** The MCP server requires the ProduckAI backend API to be running at http://localhost:8000. See Part 0 for setup instructions.

---

## Part 0: Backend Setup (10 minutes)

**⚠️  CRITICAL:** The MCP server calls the ProduckAI backend API. You MUST have the backend running before testing.

### Step 1: Start the Backend

Open a **separate terminal window** and keep it running:

```bash
# Navigate to the backend directory
cd ~/claude-code/produckai

# Activate backend virtual environment (if you have one) or use system Python
# Option A: If you have a backend venv
source venv/bin/activate

# Option B: Use system Python
# (no activation needed)

# Start the backend
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process [12345] using StatReload
# INFO:     Started server process [12346]
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
```

**Keep this terminal window open** - don't close it during testing.

### Step 2: Verify Backend is Running

In a **new terminal window**, test the backend:

```bash
# Test health endpoint
curl http://localhost:8000/healthz

# Expected response:
# {"status":"ok","database":"connected"}
```

If you see this response, the backend is ready! ✅

### Step 3: Common Backend Issues

**Problem:** "connection refused" when testing curl

**Solution:**
```bash
# Check if backend is actually running
lsof -i :8000
# Should show Python process on port 8000

# If nothing is running:
# 1. Check the backend terminal for errors
# 2. Make sure you ran uvicorn from the correct directory
# 3. Check that port 8000 isn't used by another process
```

**Problem:** "database disconnected" in health check

**Solution:**
```bash
# Backend needs PostgreSQL (or SQLite for testing)
# Check backend configuration in apps/api/config.py
```

**✅ Backend Setup COMPLETE if:**
- Backend is running on http://localhost:8000
- Health check returns {"status":"ok"}
- Terminal shows "Application startup complete"

**Now proceed to Part 1** with the backend running in the background.

---

## Part 1: Fresh Installation Test (20 minutes)

### Step 1: Prepare Clean Environment

**macOS/Linux:**
```bash
# Open Terminal
# Navigate to a test directory (NOT the development directory)
cd ~/Desktop
mkdir produckai-test
cd produckai-test

# Verify Python version
python3 --version
# Should show: Python 3.11.x or higher
```

**Windows:**
```powershell
# Open PowerShell or Command Prompt
# Navigate to a test directory
cd Desktop
mkdir produckai-test
cd produckai-test

# Verify Python version
python --version
# Should show: Python 3.11.x or higher
```

### Step 2: Create Virtual Environment

**macOS/Linux:**
```bash
# Create virtual environment
python3 -m venv test-venv

# Activate virtual environment
source test-venv/bin/activate

# Verify activation (prompt should show (test-venv))
which python
# Should show: /Users/.../produckai-test/test-venv/bin/python
```

**Windows:**
```powershell
# Create virtual environment
python -m venv test-venv

# Activate virtual environment
test-venv\Scripts\activate

# Verify activation (prompt should show (test-venv))
where python
# Should show: ...\produckai-test\test-venv\Scripts\python.exe
```

### Step 3: Get the Source Code

**⚠️  CRITICAL:** You need the source code to install the MCP server (not yet on PyPI).

**Option A: Clone from GitHub (Recommended for testers)**
```bash
# Return to test directory
cd ~/Desktop/produckai-test

# Clone the repository
git clone https://github.com/yourusername/produckai-mcp-server.git
# (Replace with actual GitHub URL once public)

# For now, copy from local development directory:
cp -r /path/to/produckai-mcp-server ./produckai-mcp-server
```

**Option B: Use existing local source (For internal testing)**
```bash
# If you already have the source code locally:
# Copy it to your test directory
cp -r ~/claude-code/produckai/github-release/produckai-mcp-server ~/Desktop/produckai-test/
```

### Step 4: Install the Package

**Make sure your venv is activated first!**

```bash
# Verify venv is active (should see (test-venv) in prompt)
which python
# Should show: ~/Desktop/produckai-test/test-venv/bin/python

# Navigate to the source directory
cd ~/Desktop/produckai-test/produckai-mcp-server

# Install in editable mode with all dependencies
pip install -e ".[dev]"

# This will take 2-3 minutes and install:
# - Core dependencies (anthropic, mcp, etc.)
# - Integration dependencies (slack-sdk, jira, etc.)
# - Development tools (pytest, black, ruff, mypy)
```

**Expected output:**
```
Successfully installed produckai-mcp-server-0.7.0
+ 50+ other packages
```

**⚠️  Common Mistake:** Don't install from the development directory! Always install from the test directory to simulate a real user installation.

### Step 5: Verify Installation

```bash
# Check command is available
which produckai-mcp
# macOS/Linux: Should show path to produckai-mcp in venv
# Windows: where produckai-mcp

# Check version
produckai-mcp --version
# Should show: produckai-mcp-server v0.7.0 (or similar)

# Test Python import
python -c "import produckai_mcp; print('Import successful')"
# Should print: Import successful

# Check installed version
python -c "import produckai_mcp; print(produckai_mcp.__version__)"
# Should show: 0.7.0
```

**✅ Installation Test PASSED if:**
- Command `produckai-mcp` is found
- Version shows 0.7.0
- Python import works
- No error messages

### Visual Verification Checklist

Before proceeding to Part 2, verify your setup matches this checklist:

**Directory Structure:**
```
~/Desktop/produckai-test/
├── produckai-mcp-server/          # Source code
│   ├── src/
│   ├── pyproject.toml
│   └── setup.py
└── test-venv/                     # Virtual environment
    ├── bin/                       # macOS/Linux
    │   ├── python
    │   ├── pip
    │   └── produckai-mcp          # ← THIS FILE MUST EXIST
    └── lib/
```

**Quick Verification Commands:**
```bash
# 1. Are you in the right directory?
pwd
# Should show: /Users/yourusername/Desktop/produckai-test

# 2. Is venv activated?
which python
# Should show: /Users/yourusername/Desktop/produckai-test/test-venv/bin/python
# NOT: /usr/bin/python or /usr/local/bin/python

# 3. Does the command exist?
ls -la test-venv/bin/produckai-mcp
# Should show: -rwxr-xr-x ... produckai-mcp
# NOT: "No such file or directory"

# 4. Can you run the command?
produckai-mcp --version
# Should show: produckai-mcp-server v0.7.0
# NOT: "command not found"
```

**⚠️  STOP and troubleshoot if ANY of these fail:**
- ❌ Wrong directory → `cd ~/Desktop/produckai-test`
- ❌ Venv not activated → `source test-venv/bin/activate`
- ❌ Command doesn't exist → Reinstall: `pip install -e "./produckai-mcp-server[dev]"`
- ❌ Command not found → Restart terminal and reactivate venv

**✅ Only proceed to Part 2 if ALL checks pass!**

---

## Part 2: Claude Desktop Configuration Test (10 minutes)

### Step 1: Locate Claude Desktop Config

**macOS:**
```bash
# Check if config exists
ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json

# If doesn't exist, create directory
mkdir -p ~/Library/Application\ Support/Claude

# Open config in text editor
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Linux:**
```bash
# Check if config exists
ls -la ~/.config/Claude/claude_desktop_config.json

# If doesn't exist, create directory
mkdir -p ~/.config/Claude

# Open config in text editor
nano ~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```powershell
# Check if config exists
dir $env:APPDATA\Claude\claude_desktop_config.json

# If doesn't exist, create directory
New-Item -ItemType Directory -Force -Path $env:APPDATA\Claude

# Open config in text editor
notepad $env:APPDATA\Claude\claude_desktop_config.json
```

### Step 2: Verify Command Path (CRITICAL!)

**⚠️  DO THIS FIRST:** Verify the command exists before adding to config!

```bash
# Make sure you're in your test directory with venv activated
cd ~/Desktop/produckai-test
source test-venv/bin/activate

# Get the FULL path to produckai-mcp
which produckai-mcp

# Expected output (macOS/Linux):
# /Users/yourusername/Desktop/produckai-test/test-venv/bin/produckai-mcp

# VERIFY the file actually exists
ls -la $(which produckai-mcp)
# Should show: -rwxr-xr-x ... produckai-mcp
```

**Windows:**
```powershell
cd Desktop\produckai-test
test-venv\Scripts\activate

# Get the FULL path
where produckai-mcp

# Expected output:
# C:\Users\YourName\Desktop\produckai-test\test-venv\Scripts\produckai-mcp.exe

# VERIFY the file exists
dir (where produckai-mcp)
```

**⚠️  STOP HERE if:**
- Command not found → Go back to Part 1, Step 4 (Install the package)
- Path doesn't show test-venv → Wrong venv is activated
- File doesn't exist → Installation failed

**✅ ONLY proceed if `which produckai-mcp` returns a valid path!**

### Step 3: Add Configuration

**IMPORTANT:** Use the EXACT FULL PATH from Step 2 above.

**macOS/Linux example:**
```json
{
  "mcpServers": {
    "produckai": {
      "command": "/Users/yourusername/Desktop/produckai-test/test-venv/bin/produckai-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-your-actual-api-key-here",
        "PRODUCKAI_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

**Windows example:**
```json
{
  "mcpServers": {
    "produckai": {
      "command": "C:\\Users\\YourName\\Desktop\\produckai-test\\test-venv\\Scripts\\produckai-mcp.exe",
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-your-actual-api-key-here",
        "PRODUCKAI_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

**⚠️  CRITICAL MISTAKES TO AVOID:**
- ❌ Don't use relative paths (e.g., `./test-venv/bin/produckai-mcp`)
- ❌ Don't copy example paths - use YOUR actual path from Step 2!
- ❌ Don't forget to replace `yourusername` with your actual username
- ❌ Don't forget to add your real Anthropic API key
- ✅ Copy the exact path from `which produckai-mcp` in Step 2

### Step 4: Verify Configuration

```bash
# Check config file is valid JSON
python -m json.tool < ~/Library/Application\ Support/Claude/claude_desktop_config.json
# macOS - should show formatted JSON with no errors

python -m json.tool < ~/.config/Claude/claude_desktop_config.json
# Linux - should show formatted JSON with no errors

python -m json.tool < $env:APPDATA\Claude\claude_desktop_config.json
# Windows - should show formatted JSON with no errors
```

**Extra Verification: Check the command path exists**
```bash
# macOS/Linux - verify path from config actually exists
ls -la /Users/yourusername/Desktop/produckai-test/test-venv/bin/produckai-mcp
# Should show file exists (not "No such file or directory")

# Windows
dir C:\Users\YourName\Desktop\produckai-test\test-venv\Scripts\produckai-mcp.exe
```

**⚠️  If you get "No such file or directory":**
- Your config has the WRONG path
- Go back to Step 2 and get the correct path
- This is the #1 cause of "Could not connect to MCP server" errors!

### Step 5: Restart Claude Desktop

**macOS:**
```bash
# Completely quit Claude Desktop (Cmd+Q or right-click dock icon → Quit)
# Do NOT just close the window
# Wait 5 seconds
# Reopen Claude Desktop from Applications
```

**Linux:**
```bash
# Kill Claude process
pkill -9 claude
# Wait 5 seconds
# Restart Claude Desktop
```

**Windows:**
```powershell
# Close Claude Desktop completely
# Right-click taskbar icon → Close window
# Wait 5 seconds
# Reopen from Start Menu
```

### Step 6: Verify Connection in Claude Desktop

Open Claude Desktop and type:

```
"List the available ProduckAI tools"
```

**Expected Response:**
- Claude should show a list of tools
- You should see mentions of: upload_csv_feedback, run_clustering, calculate_voc_scores, generate_prd
- Tool count should be around 50 tools

**✅ Configuration Test PASSED if:**
- Claude Desktop shows ProduckAI tools
- No error messages about MCP server
- Tools are accessible

---

## Part 3: Basic Functionality Test (15 minutes)

**⚠️  PREREQUISITE:** Ensure the backend is running (see Part 0). The MCP server will fail if the backend is not accessible.

### Test 1: Demo Data Workflow

**Step 1: Verify Backend Connection**

In Claude Desktop, first verify the MCP server can reach the backend:

```
"Check if the ProduckAI backend is running"
```

**Expected Response:**
- Should confirm backend is accessible
- May show backend status and version

If you get "backend not running" error, go back to Part 0 and start the backend.

**Step 2: Copy demo data to test directory**

```bash
# From your test directory
cd ~/Desktop/produckai-test

# Copy demo data from github-release
cp -r /Users/rohitsaraf/claude-code/produckai/github-release/produckai-mcp-server/demo-data .

# Verify it's there
ls -la demo-data/
# Should show: feedback.csv, customers.json, README.md
```

**Step 3: Upload demo feedback**

In Claude Desktop:
```
"Upload the demo feedback CSV at ~/Desktop/produckai-test/demo-data/feedback.csv"
```

**Expected Response:**
- Claude should confirm upload
- Should show: "Successfully uploaded X feedback items" or "Successfully processed X file(s)"
- Number should be around 50 items
- Backend terminal should show API requests

**Note:** The MCP server uploads files to the backend via `/upload/upload-feedback` endpoint.

**Step 4: Run clustering**

In Claude Desktop:
```
"Run clustering on the feedback to identify themes"
```

**Expected Response:**
- Should take 1-2 minutes
- Should show: "Clustering completed" or "Clustering task started"
- Should show: X themes identified
- Should show: X insights generated
- Backend terminal will show processing activity

**Note:** Clustering happens in the backend. You can see logs in the backend terminal.

**Step 5: View themes**

In Claude Desktop:
```
"Show me the top 5 themes by feedback count"
```

**Expected Response:**
- List of 5 insights (backend calls them insights, but MCP may present as themes)
- Each with: title, feedback count, description, priority score
- Insights should make sense (API features, UI improvements, etc.)

**Note:** The backend endpoint is `/themes` which returns insights. This is expected.

**Step 6: Calculate VOC scores**

In Claude Desktop:
```
"Calculate VOC scores for all insights"
```

**Expected Response:**
- Should complete in < 30 seconds
- Should show: "VOC scores calculated for X insights" or similar success message
- Scores should be 0-100 scale
- Backend may show VOC calculation requests

**Step 7: Get top priorities**

In Claude Desktop:
```
"Show me the top 5 insights by VOC score"
```

**Expected Response:**
- List of 5 insights ranked by priority
- Each with: title, VOC score (or priority_score), description, severity
- Scores should be in descending order

**Step 8: Generate PRD**

In Claude Desktop:
```
"Generate a PRD for the highest-priority insight"
```

**Expected Response:**
- Should take 10-15 seconds
- Should generate a complete PRD document
- PRD should include: Executive Summary, Problem Statement, Solution, Success Metrics
- Uses Claude Sonnet 4.5 for generation (calls backend `/themes/{id}/generate-prd`)

**Step 9: Export PRD**

In Claude Desktop:
```
"Export that PRD to ~/Desktop/test-prd.md"
```

**Expected Response:**
- Should confirm export
- File should be created at ~/Desktop/test-prd.md

**Verify the export:**
```bash
# Check file exists
ls -la ~/Desktop/test-prd.md

# View the content
cat ~/Desktop/test-prd.md
# Should show a complete PRD in markdown format
```

**✅ Basic Functionality Test PASSED if:**
- All 9 steps completed successfully
- Backend is running and responsive
- Demo data uploaded to backend
- Clustering generated insights/themes
- VOC scoring worked
- PRD was generated and exported
- No error messages in Claude Desktop or backend terminal

---

## Part 4: Integration Testing (Optional, 30-60 minutes)

### Test 1: Slack Integration (15 minutes)

**Prerequisites:**
- Slack workspace admin access
- Ability to create apps

**Steps:**

1. **Setup Slack integration**
   ```
   "Setup Slack integration"
   ```
   Follow the OAuth flow in browser

2. **List channels**
   ```
   "List available Slack channels"
   ```
   Should show your workspace channels

3. **Test sync** (use a test channel with a few messages)
   ```
   "Sync the #test channel for the last 2 days"
   ```
   Should sync messages and classify them

**✅ PASSED if:** OAuth completes, channels listed, sync works

### Test 2: Google Drive Integration (15 minutes)

**Prerequisites:**
- Google account
- Google Cloud project with APIs enabled

**Steps:**

1. **Setup Google Drive**
   ```
   "Setup Google Drive integration"
   ```
   Follow OAuth flow

2. **Browse folders**
   ```
   "Browse my Google Drive folders"
   ```
   Should show your Drive folders

3. **Preview folder** (use a small test folder)
   ```
   "Preview the 'Test Folder' folder"
   ```
   Should show file count and cost estimate

**✅ PASSED if:** OAuth completes, folders listed, preview works

### Test 3: CSV Upload (5 minutes)

**Steps:**

1. **Get template**
   ```
   "Show me CSV templates"
   ```
   Should list available templates

2. **Upload custom CSV**
   Create a simple CSV:
   ```csv
   text,customer_name,created_at
   "Test feedback 1","Test Corp","2025-01-15T10:00:00Z"
   "Test feedback 2","Test Inc","2025-01-16T11:00:00Z"
   ```

   Save as `~/Desktop/test-feedback.csv`

   ```
   "Upload CSV feedback from ~/Desktop/test-feedback.csv"
   ```
   Should upload 2 items

**✅ PASSED if:** Template shown, CSV uploaded successfully

---

## Part 5: Error Handling Test (10 minutes)

### Test 1: Backend Down Error

**Stop the backend temporarily:**
```bash
# In the backend terminal, press Ctrl+C to stop it
```

In Claude Desktop:
```
"Upload CSV feedback from ~/Desktop/produckai-test/demo-data/feedback.csv"
```

**Expected:** Clear error message about backend not accessible, not a crash

**Restart the backend:**
```bash
# In backend terminal
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Test 2: Invalid Input

In Claude Desktop:
```
"Upload CSV feedback from /nonexistent/file.csv"
```

**Expected:** Clear error message about file not found, not a crash

### Test 3: Empty Feedback

```
"Calculate VOC scores for all insights"
```
(Before uploading any feedback)

**Expected:** Info message about no insights available, not a crash

### Test 4: Invalid Commands

```
"Generate a PRD for insight ID that-doesnt-exist"
```

**Expected:** Error message about insight not found (404 from backend)

**✅ Error Handling Test PASSED if:**
- Backend down error is handled gracefully
- File not found errors are clear
- Empty data scenarios handled
- Invalid IDs return clear errors
- No crashes or stack traces in Claude Desktop
- Backend errors (404, 500) are translated to user-friendly messages

---

## Part 6: Performance Test (5 minutes)

### Test 1: Large CSV Upload

Create a CSV with 100 rows:
```python
# Run this in Python to generate test data
import csv
from datetime import datetime, timedelta

with open('/Users/rohitsaraf/Desktop/large-feedback.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['text', 'customer_name', 'created_at'])
    for i in range(100):
        date = datetime.now() - timedelta(days=i)
        writer.writerow([
            f'Test feedback item {i}',
            f'Customer {i % 10}',
            date.isoformat()
        ])

print("Created large-feedback.csv with 100 items")
```

In Claude Desktop:
```
"Upload CSV feedback from ~/Desktop/large-feedback.csv"
```

**Expected:**
- Should complete in < 10 seconds
- Should upload all 100 items
- No timeouts or errors

### Test 2: Clustering Performance

```
"Run clustering on the feedback"
```

**Expected:**
- Should complete in 2-3 minutes for 100 items
- Should not timeout
- Should generate themes

**✅ Performance Test PASSED if:**
- Large uploads work
- Clustering completes in reasonable time
- No timeouts

---

## Part 7: Cleanup and Reset (5 minutes)

### Test Database Reset

```bash
# Check state database location
ls -la ~/.produckai/state.db

# Backup current state
cp ~/.produckai/state.db ~/.produckai/state.db.backup

# View database size
du -h ~/.produckai/state.db
```

### Test Fresh Start

```bash
# Remove state database
rm ~/.produckai/state.db

# Restart Claude Desktop

# Try uploading demo data again
```

In Claude Desktop:
```
"Upload the demo feedback CSV at ~/Desktop/produckai-test/demo-data/feedback.csv"
```

**Expected:** Should work as if fresh install

**✅ Cleanup Test PASSED if:**
- Can reset state
- Fresh start works
- No orphaned data

---

## Final Verification Checklist

### Installation ✅
- [ ] Package installs without errors
- [ ] Command `produckai-mcp` is available
- [ ] Version is 0.7.0
- [ ] Python import works

### Claude Desktop Integration ✅
- [ ] Config file is valid JSON
- [ ] MCP server connects
- [ ] Tools are listed (50 tools)
- [ ] Commands execute successfully

### Core Functionality ✅
- [ ] CSV upload works
- [ ] Clustering generates themes
- [ ] VOC scoring calculates priorities
- [ ] PRD generation creates documents
- [ ] PRD export saves files

### Error Handling ✅
- [ ] Invalid inputs handled gracefully
- [ ] Clear error messages shown
- [ ] No crashes or stack traces

### Performance ✅
- [ ] Large datasets (100+ items) work
- [ ] Clustering completes in reasonable time
- [ ] No timeouts

### Documentation Accuracy ✅
- [ ] Installation instructions work
- [ ] Commands in docs are correct
- [ ] Expected outputs match reality
- [ ] Troubleshooting tips are helpful

---

## Common Issues and Solutions

### Issue 1: Command not found

**Problem:** `produckai-mcp: command not found`

**Solution:**
```bash
# Verify venv is activated
which python
# Should show venv path

# If not activated:
source test-venv/bin/activate  # macOS/Linux
test-venv\Scripts\activate     # Windows

# Reinstall if needed
pip install -e ".[dev]"
```

### Issue 2: Claude Desktop doesn't show tools

**Problem:** Tools not appearing in Claude Desktop

**Solution:**
```bash
# 1. Verify config path is correct
which produckai-mcp
# Copy this FULL path to config

# 2. Verify config is valid JSON
python -m json.tool < ~/Library/Application\ Support/Claude/claude_desktop_config.json

# 3. Completely quit and restart Claude Desktop
# Don't just close window - use Cmd+Q (Mac) or right-click → Quit
```

### Issue 2A: "Could not connect to MCP server" or "spawn ENOENT" Error

**Problem:** Claude Desktop shows error:
```
⚠️  Could not connect to MCP server produckai
⚠️  MCP produckai: spawn /path/to/python ENOENT
```

**What ENOENT means:** "Error NO ENTry" = File not found at the specified path

**Root Cause:** Your `claude_desktop_config.json` has the WRONG path to the MCP server command.

**Solution - Step by Step:**

**Step 1: Verify what path is in your config**
```bash
# macOS/Linux
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | grep command

# Windows
type %APPDATA%\Claude\claude_desktop_config.json | findstr command
```

**Step 2: Verify if that path actually exists**
```bash
# Copy the path from Step 1 and check if it exists
# macOS/Linux example:
ls -la /Users/rohitsaraf/Desktop/produckai-mcp-server/venv/bin/python
# If you get "No such file or directory" - that's the problem!

# Windows example:
dir C:\Users\YourName\Desktop\produckai-mcp-server\venv\Scripts\python.exe
```

**Step 3: Find the CORRECT path**
```bash
# Activate your venv
cd ~/Desktop/produckai-test
source test-venv/bin/activate  # macOS/Linux
# test-venv\Scripts\activate  # Windows

# Get the correct path
which produckai-mcp  # macOS/Linux
# where produckai-mcp  # Windows

# This is the path you should use!
```

**Step 4: Update your config with the CORRECT path**
```bash
# Open config file
open ~/Library/Application\ Support/Claude/claude_desktop_config.json  # macOS
# nano ~/.config/Claude/claude_desktop_config.json  # Linux
# notepad %APPDATA%\Claude\claude_desktop_config.json  # Windows

# Replace the "command" value with the path from Step 3
```

**Step 5: Verify the path exists**
```bash
# Use the exact path from your config
ls -la /Users/yourusername/Desktop/produckai-test/test-venv/bin/produckai-mcp
# Should show file exists (NOT "No such file or directory")
```

**Step 6: Completely quit and restart Claude Desktop**
```bash
# macOS: Cmd+Q (not just close window!)
# Windows: Right-click taskbar → Quit
# Wait 5 seconds, then reopen
```

**Common Wrong Paths:**
- ❌ `/Users/rohitsaraf/Desktop/produckai-mcp-server/venv/bin/python` (copied from example)
- ❌ `./test-venv/bin/produckai-mcp` (relative path)
- ❌ `/path/to/produckai-mcp` (placeholder not replaced)
- ✅ `/Users/yourusername/Desktop/produckai-test/test-venv/bin/produckai-mcp` (actual path)

**Prevention:** ALWAYS verify the path exists (Step 2 in Part 2) BEFORE adding it to config!

### Issue 3: Backend not running

**Problem:** "Backend not running" or "Connection refused" errors

**Solution:**
```bash
# Check if backend is running
curl http://localhost:8000/healthz

# If connection refused:
# 1. Go to backend terminal - is uvicorn running?
# 2. Start backend:
cd ~/claude-code/produckai
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# 3. Verify:
curl http://localhost:8000/healthz
# Should return: {"status":"ok","database":"connected"}
```

### Issue 4: API errors

**Problem:** "Failed to connect to Anthropic API"

**Solution:**
```bash
# Test API key manually
export ANTHROPIC_API_KEY="your-key"
python -c "from anthropic import Anthropic; print(Anthropic().messages.create(model='claude-3-haiku-20240307', max_tokens=10, messages=[{'role':'user','content':'hi'}]))"

# If this fails, API key is invalid
# Get new key from: https://console.anthropic.com/settings/keys
```

### Issue 5: Demo data not found

**Problem:** "File not found: demo-data/feedback.csv"

**Solution:**
```bash
# Use absolute path
cd ~/Desktop/produckai-test
ls -la demo-data/feedback.csv

# In Claude, use full path:
"Upload the demo feedback CSV at /Users/rohitsaraf/Desktop/produckai-test/demo-data/feedback.csv"
```

### Issue 6: 404 errors from backend

**Problem:** Tools work but return "404 Not Found" errors

**Solution:**
```bash
# This means MCP server and backend API endpoints don't match
# This should NOT happen after the API client fixes, but if it does:

# 1. Check backend version
curl http://localhost:8000/openapi.json | grep -o '"version":"[^"]*"'

# 2. Check MCP client is using correct endpoints
# Review ~/claude-code/produckai/github-release/produckai-mcp-server/docs/FIXES_APPLIED.md

# 3. Ensure you're testing the UPDATED MCP server (with API client fixes)
pip show produckai-mcp-server
# Should be installed from the github-release directory
```

---

## Test Results Template

Copy this and fill it out as you test:

```
## Pre-Release Testing Results

**Date:** [Date]
**Tester:** [Your Name]
**Platform:** [macOS 14 / Ubuntu 22.04 / Windows 11]
**Python Version:** [3.11.x / 3.12.x / 3.13.x]

### Part 1: Installation
- [ ] PASS / FAIL - Installation completed without errors
- [ ] PASS / FAIL - Command available
- [ ] PASS / FAIL - Version correct (0.7.0)
- Notes: ___________

### Part 2: Claude Desktop Config
- [ ] PASS / FAIL - Config file created
- [ ] PASS / FAIL - Tools appear in Claude Desktop
- [ ] PASS / FAIL - Connection successful
- Notes: ___________

### Part 3: Basic Functionality
- [ ] PASS / FAIL - Demo data uploaded
- [ ] PASS / FAIL - Clustering worked
- [ ] PASS / FAIL - VOC scoring worked
- [ ] PASS / FAIL - PRD generated
- [ ] PASS / FAIL - PRD exported
- Notes: ___________

### Part 4: Integrations (Optional)
- [ ] PASS / FAIL / SKIP - Slack integration
- [ ] PASS / FAIL / SKIP - Google Drive integration
- [ ] PASS / FAIL / SKIP - CSV upload
- Notes: ___________

### Part 5: Error Handling
- [ ] PASS / FAIL - Errors handled gracefully
- [ ] PASS / FAIL - Clear error messages
- Notes: ___________

### Part 6: Performance
- [ ] PASS / FAIL - Large dataset (100 items)
- [ ] PASS / FAIL - Clustering performance acceptable
- Notes: ___________

### Overall Result
- [ ] READY FOR RELEASE
- [ ] NEEDS FIXES (list below)

Issues Found:
1. ___________
2. ___________
3. ___________
```

---

## Next Steps After Testing

### If All Tests Pass ✅
1. Document test results
2. Proceed with PyPI publishing (Week 2, Days 8-11)
3. Make GitHub repository public

### If Issues Found ❌
1. Document specific failures
2. Fix issues in development directory
3. Copy fixes to github-release clone
4. Re-test
5. Update Day 3 summary if documentation changes needed

---

**Testing Time Estimate:**
- Part 0 (Backend setup): ~10 minutes
- Minimum (Parts 0-3): ~55 minutes
- With integrations (Parts 0-4): ~100 minutes
- With all optional tests: ~130 minutes

**Recommendation:**
1. **ALWAYS do Part 0 first** - backend must be running
2. Then do Parts 1-3 to validate core functionality
3. Add integration tests if time permits (Part 4)

**Important:** Keep the backend terminal open and running throughout all tests!

---

**Ready to test? Start with Part 1: Fresh Installation Test** ✅
