# Enterprise RAG Streamlit UI

Production-grade web interface for the RAG system.

## Features

✅ **Chat Interface** - Interactive Q&A with conversation history
✅ **Source Display** - See which documents answered your question  
✅ **Confidence Scores** - Track answer reliability
✅ **Performance Metrics** - Monitor response times
✅ **History Export** - Download conversations as JSON
✅ **Health Monitoring** - Check API status from UI
✅ **Input Validation** - Client-side query validation
✅ **Error Handling** - Clear error messages with recovery

## Installation

```bash
# Install Streamlit (already in requirements.txt)
pip install streamlit

# Or add to your requirements.txt:
# streamlit>=1.28.0
```

## Running

### Option 1: Run API + UI Together (Recommended)

**Terminal 1 - Start FastAPI:**
```bash
cd e:\enterprise_rag
python -m uvicorn api.routes:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 - Start Streamlit:**
```bash
cd e:\enterprise_rag
streamlit run ui/streamlit_app.py --server.port 8501 --server.address 127.0.0.1
```

Then open browser: http://localhost:8501

### Option 2: Docker Compose (Production)

```bash
docker-compose up -d
# API: http://localhost:8000
# UI: http://localhost:8501
```

## Configuration

**In Streamlit Sidebar:**
1. Set API Endpoint: `http://localhost:8000` (or your production URL)
2. Enter API Key: Copy a valid key from `.env` (`SERVICE_API_KEY` or `SERVICE_API_KEYS`)
3. Toggle settings: Confidence, Sources, Response Times
4. Click "Check API Status" to verify connection

## Features Explained

| Feature | Purpose |
|---------|---------|
| **Chat Tab** | Real-time Q&A interface with conversation |
| **History Tab** | Review past queries, answers, and metadata |
| **Metrics Tab** | Dashboard showing confidence, latency, source usage |
| **Source Display** | Links to documents used for answer |
| **Confidence Score** | 0-100% reliability of answer (from hybrid scoring) |
| **Response Time** | Milliseconds to generate answer |

## Deployment

### Production Setup

```bash
# 1. Update API URL in config
# Edit ui/streamlit_app.py or set environment variable

# 2. Run with Streamlit config
streamlit run ui/streamlit_app.py \
  --server.port 80 \
  --server.address 0.0.0.0 \
  --logger.level=warning

# 3. Or use Gunicorn wrapper (coming next)
```

### Remote Access

To access UI from another machine:
```bash
streamlit run ui/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

Then visit: `http://YOUR_SERVER_IP:8501`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot connect to API" | Ensure FastAPI server is running on port 8000 |
| "API Key invalid" | Check `.env` key config (`SERVICE_API_KEY` / `SERVICE_API_KEYS`) matches sidebar |
| "Query too long" | Keep under 500 characters |
| "Rate limited (503)" | Wait 60 seconds, then retry |
| "Response timeout (504)" | API took >30s, check server logs |

## Architecture

```
Streamlit UI (Port 8501)
    ↓ HTTP Requests
FastAPI Backend (Port 8000)
    ↓ Process query
    ├─ Retrieve documents (FAISS + BM25)
    ├─ Check embeddings cache
    ├─ Generate answer (OpenAI)
    └─ Return with confidence + sources
    ↑ HTTP Response
Streamlit UI (Display result)
```

## Next Steps

- [ ] Add dark mode toggle
- [ ] Add document upload feature
- [ ] Add citation/inline sources
- [ ] Add batch query processing
- [ ] Add user authentication
- [ ] Add usage analytics

## Files

- `streamlit_app.py` - Main Streamlit application
- `.streamlit/config.toml` - Streamlit configuration (optional)

---

**Internal-Pilot Ready**: This UI is configured for internal use with proper error handling, validation, and monitoring.
