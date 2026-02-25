# Quick Start Guide - Running Streamlit UI

## Prerequisites
✅ FastAPI API running on `http://localhost:8000`
✅ `SERVICE_API_KEY` (or `SERVICE_API_KEYS`) from `.env`
✅ Python 3.10+

## 🚀 Start in 3 Steps

### Step 1: Install Streamlit (if not already installed)
```bash
cd e:\enterprise_rag
pip install streamlit requests
```

### Step 2: Start FastAPI Backend
**Open Terminal 1:**
```bash
cd e:\enterprise_rag
# Activate venv
.venv\Scripts\activate

# Start API server
python -m uvicorn api.routes:app --reload --host 127.0.0.1 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 3: Start Streamlit UI
**Open Terminal 2:**
```bash
cd e:\enterprise_rag
# Activate venv
.venv\Scripts\activate

# Start Streamlit
streamlit run ui/streamlit_app.py
```

Expected output:
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
```

## 📱 Access the UI
Open your browser and go to: **http://localhost:8501**

## Configuration in UI

1. **Sidebar - API Endpoint**: `http://localhost:8000`
2. **Sidebar - API Key**: Paste a valid key from `SERVICE_API_KEY` or `SERVICE_API_KEYS` in `.env`
3. **Optional - Settings**: Toggle confidence, sources, response times
4. **Click "Check API Status"** to verify connection

## Example Questions to Try
- "What is the data governance policy?"
- "How should we handle security incidents?"
- "What are the AI governance requirements?"
- "What is the risk management framework?"

## Troubleshooting

### "Cannot connect to API"
```bash
# Check if API is running
curl http://localhost:8000/health

# If not, start it in Terminal 1:
python -m uvicorn api.routes:app --reload
```

### "API Key invalid"
```bash
# Check .env file has SERVICE_API_KEY or SERVICE_API_KEYS
# Example: SERVICE_API_KEY=change-me
cat .env | grep SERVICE_API_KEY
```

### "Streamlit not found"
```bash
# Install it
pip install streamlit
```

### "Port 8501 already in use"
```bash
# Use different port
streamlit run ui/streamlit_app.py --server.port 8502
```

## Running as Daemon (Background)

**Use tmux on Linux/macOS:**
```bash
tmux new-session -d -s api "python -m uvicorn api.routes:app"
tmux new-session -d -s ui "streamlit run ui/streamlit_app.py"
```

**Use nohup on Windows PowerShell:**
```bash
nohup python -m uvicorn api.routes:app > api.log 2>&1 &
nohup streamlit run ui/streamlit_app.py > ui.log 2>&1 &
```

## Production Deployment

### Docker Compose (Recommended)
```bash
# Ensure .env has OPENAI_API_KEY and SERVICE_API_KEY (or SERVICE_API_KEYS)
docker-compose up -d

# Access:
# API: http://localhost:8000
# UI: http://localhost:8501
# Check logs: docker-compose logs -f
```

### Manual Production Start
```bash
# Start API
gunicorn -w 4 -b 0.0.0.0:8000 api.routes:app &

# Start UI
streamlit run ui/streamlit_app.py \
  --server.port 80 \
  --server.address 0.0.0.0 \
  --logger.level=warning
```

## Features Available in UI

| Tab | Features |
|-----|----------|
| **💬 Chat** | Real-time Q&A, conversation history, typing indicator |
| **📚 History** | Past queries, answers, sources, export to JSON |
| **📊 Metrics** | Confidence distribution, response time trends, source popularity |

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Send Query | Enter or Click "Send" |
| Clear History | Click "🗑️ Clear Conversation" |
| Export History | Click "💾 Export History as JSON" |
| Refresh | F5 or Cmd+R |

## API Integration

The Streamlit app calls:
- `GET /health` - Check API status
- `POST /ask` - Send query and get answer
- `GET /metrics` - Internal metrics (requires API key)

`/health` response now includes readiness fields:
- `rag_initialized`
- `init_error`

Example raw request:
```bash
curl -X POST http://localhost:8000/ask \
  -H "x-api-key: change-me" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is AI governance?"}'
```

Expected response:
```json
{
  "answer": "AI governance refers to...",
  "confidence": 0.45,
  "sources": ["07_AI_Governance_Policy", "09_AI_Model_Validation_SOP"],
  "latency_ms": 2540
}
```

## Performance Tips

- **Caching**: First 10 documents cached in DB (1866x faster on 2nd run)
- **Async**: Queries processed asynchronously (1.3x faster)
- **Rate Limit**: 5 queries/minute per IP (configurable in `slowapi`)
- **Timeout**: Max 30 seconds per query (configurable)

## Need Help?

See `ui/README.md` for full documentation
