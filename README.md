# Enterprise RAG (Internal Pilot)

Production-style internal Retrieval-Augmented Generation (RAG) system for policy/compliance document Q&A.

## Overview
This project provides an internal assistant that answers questions from enterprise documents with source-backed responses.

Core flow:
1. Ingest and chunk PDFs
2. Retrieve relevant context with hybrid search (FAISS + BM25)
3. Generate grounded answers with OpenAI
4. Return answer, confidence, sources, and latency

## Tech Stack
- Python, FastAPI, Streamlit
- FAISS (semantic retrieval), BM25 (keyword retrieval)
- OpenAI (`text-embedding-3-small`, `gpt-4o-mini`)
- SQLite embeddings cache
- Pytest test suite

## Key Features
- Hybrid retrieval (`60% semantic + 40% keyword`)
- Source-cited responses
- Confidence scoring
- Retry/backoff + typed error handling
- API key auth (single-key and multi-key env formats)
- Rate limiting (`5/min`)
- Startup prewarm for first-request latency reduction
- Health + metrics endpoints (`/health`, `/metrics`)

## Project Structure
```text
api/          FastAPI routes, service, security, exceptions
ingestion/    PDF loading and chunking
retriever/    FAISS, BM25, hybrid scoring
llm/          OpenAI clients, prompting
ui/           Streamlit app
tests/        Test suite
```

## Local Run
1. Create and activate virtualenv
2. Install deps:
```bash
pip install -r requirements.txt
```
3. Configure env:
```env
OPENAI_API_KEY=your_key_here
SERVICE_API_KEY=change-me
SERVICE_API_KEYS=
CORS_ALLOW_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
```
4. Start API:
```bash
python -m uvicorn api.routes:app --host 127.0.0.1 --port 8000
```
5. Start UI:
```bash
streamlit run ui/streamlit_app.py --server.port 8501 --server.address 127.0.0.1
```

## API Endpoints
- `GET /health` -> service + readiness status
- `POST /ask` -> protected query endpoint
- `GET /metrics` -> protected internal metrics

## Testing
```bash
pytest -q
```

## Notes
- This repo is positioned as an internal production pilot.
- Interview prep docs are intentionally excluded from the published repo.
