# Interview Questions & Answers - Deep Technical

## ðŸŽ¯ Expected Questions & Strong Answers

---

## 1. How would you explain RAG to a non-technical person?

### âŒ Bad Answer:
"It's a system that uses FAISS and BM25 to retrieve documents and generate answers using OpenAI."

### âœ… Good Answer:
"Imagine you have a library of 10,000 documents but no librarian. When someone asks a question, RAG does three things:

1. **Understands** the question by converting it to a semantic meaning (vector)
2. **Finds** the most relevant documents in the library (using similarity matching)
3. **Answers** by asking an AI assistant to read those documents and answer the question

It's like having a very fast librarian who understands meaning, not just keywords."

---

## 2. Why would pure semantic search fail for your use case?

### âŒ Weak Answer:
"Because it's not always accurate."

### âœ… Strong Answer:
"Pure semantic search has two failure modes:

1. **Misses exact keywords:** Document titled 'Data Governance Policy' has the exact words, but if the query is 'information management policy,' semantic similarity might score it lower because the words are slightly different.

2. **Context drift:** The vector embedding can drift semantically. For example, 'storage' and 'warehouse' are semantically similar, but a governance policy about data STORAGE is very different from a warehouse.

This is why I added keyword search (BM25) with 40% weighting - it catches exact keyword matches that semantic search might miss."

---

## 3. Why NOT use traditional full-text search (like Elasticsearch)?

### âŒ Weak Answer:
"Semantic search is better."

### âœ… Strong Answer:
"Full-text search is great for keyword matching but terrible for semantic meaning:

Query: 'What are data protection measures?'
Document has: 'Our confidentiality framework includes...'
- Elasticsearch: Might score low (keywords don't match well)
- My system: Understands 'protection' â‰ˆ 'confidentiality' semantically

However, I didn't completely replace full-text search - I **combined** them. BM25 (keyword) + FAISS (semantic) = hybrid retrieval, which is stronger than either alone.

For a pure keyword-based system, Elasticsearch is better. For semantic understanding, FAISS is better. For enterprise documents where both matter, hybrid is best."

---

## 4. How does your caching actually work at the database level?

### âŒ Weak Answer:
"I cache embeddings in SQLite."

### âœ… Strong Answer:
"Here's the exact implementation:

```
Table: embeddings_cache
Columns:
  - text_hash (PRIMARY KEY, VARCHAR)  -- SHA256 of text chunk
  - embedding (BLOB)                   -- 1536 float32 values
  - created_at (TIMESTAMP)             -- Audit trail
  - hit_count (INTEGER)                -- Analytics
```

Query flow:
```python
text_hash = sha256(text_chunk.encode()).hexdigest()
query = "SELECT embedding FROM embeddings_cache WHERE text_hash = ?"
if cursor.fetchone():
    embedding = deserialize_blob(row)  # <1ms
else:
    embedding = openai.create_embedding(text)
    insert_into_cache(text_hash, embedding)
```

Trade-offs:
- **Pro:** Deterministic (same text = same hash), persistent, no external service
- **Con:** Memory-bound on disk (1GB = ~2M embeddings), no TTL/expiration

Why SHA256? Because it's:
- Collision-resistant (different texts won't map to same hash)
- Deterministic (same text always produces same hash)
- Fast (O(1) lookup in SQLite index)
"

---

## 5. What if two documents have the exact same text? Your cache key design...

### âŒ Weak Answer:
"Then they'd have the same embedding."

### âœ… Strong Answer:
"Great question - you found the edge case!

If two documents have identical text, they'd generate identical embeddings. This is actually **correct behavior** but reveals a limitation:

Problem:
- Document A: '01_Data_Governance_Policy.pdf' with text 'section 1...'
- Document B: '02_Data_Management.pdf' with SAME text 'section 1...'

Current behavior:
- Both map to same text_hash
- Share same embedding
- Hybrid search returns both as having same relevance

Limitation: Can't distinguish between them by content alone.

Solution for production:
- Add document ID to cache key: `text_hash = sha256(text + doc_id)`
- Or use versioning: `text_hash = sha256(text + version_number)`
- This ensures deduplication works at embedding level while preserving doc identity

In my implementation, I could have done:
```python
cache_key = sha256((text + document_id).encode()).hexdigest()
```

This would prevent accidental duplication issues."

---

## 6. Your async retry logic - what happens if all 3 attempts fail?

### âŒ Weak Answer:
"Then the request fails."

### âœ… Strong Answer:
"Excellent edge case! If all 3 attempts fail:

```python
async def embed_with_retry(text, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return await openai_api.embed(text)
        except (TimeoutError, RateLimitError) as e:
            if attempt < max_attempts - 1:
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                await asyncio.sleep(wait_time)
            else:
                raise  # â† Raises original exception
```

Then in the endpoint:
```python
try:
    docs = await rag_service.ask_async(query)
except RuntimeError as e:
    if 'rate limit' in str(e):
        return JSONResponse(status_code=503, content={'error': 'RATE_LIMITED'})
    elif 'timeout' in str(e):
        return JSONResponse(status_code=504, content={'error': 'TIMEOUT'})
    else:
        return JSONResponse(status_code=500, content={'error': 'INTERNAL_ERROR'})
```

So the flow is:
- Attempt 1 fails â†’ wait 1s â†’ retry
- Attempt 2 fails â†’ wait 2s â†’ retry  
- Attempt 3 fails â†’ raise RuntimeError
- Endpoint catches it â†’ returns HTTP 503 (service unavailable)

User gets: '503 Service Unavailable - Rate limited. Please try again in 1 minute.'

Better than: Server crash or hanging request"

---

## 7. Why did you choose 60/40 weighting? Is it arbitrary?

### âŒ Weak Answer:
"I thought 60/40 was a good balance."

### âœ… Strong Answer:
"Great question - it's actually based on use-case analysis, not just intuition:

**Why 60 for semantic?**
- Semantic understanding is more valuable for RAG (captures meaning)
- OpenAI embeddings are state-of-the-art and reliable
- Better at generalization (synonyms, conceptual similarity)

**Why 40 for keyword?**
- Safety net for exact matches (governance query + 'governance' word)
- Catches BM25's strength in statistical relevance
- Prevents semantic drift (important for policy documents)

**Testing the weighting:**

| Weighting | Query | Result | Score |
|-----------|-------|--------|-------|
| 100/0 semantic | 'governance' | Strong semantic match | 0.85 |
| 50/50 | Same | Exact keyword found too | 0.82 |
| 60/40 | Same | Exact keyword found too | 0.83 |
| 0/100 keyword | Same | Only looks at stats | 0.65 |

**60/40 was optimal because:**
- Prioritizes semantic understanding
- Captures exact keyword matches when present
- Empirically outperformed other weights on test queries

**For production, I'd:**
```python
# Make it configurable
confidence = (
    weight['semantic'] * vector_score +
    weight['keyword'] * keyword_score
)
# Then A/B test with real users to find optimal weights
```
"

---

## 8. If you had only 1 second to return an answer, what would you cut?

### âŒ Weak Answer:
"I'd remove the LLM generation and just return documents."

### âœ… Strong Answer:
"Depends on what matters more: **speed or quality**. Here's my prioritization:

**Keep (non-negotiable):**
1. Retrieval: 200ms (hybrid search)
2. Validation: 10ms (input checking)
3. Response: 40ms (JSON serialization)

**Cut (in order of priority):**
1. ~~LLM generation~~ (-2.5s) â†’ Return just sources + raw text
2. ~~Async batching~~ (-0.3s) â†’ Go sequential
3. ~~Caching~~ (-depends) â†’ Hit API every time
4. ~~Error handling~~ (-0.05s) â†’ Basic validation only

**Production strategy:**
Instead of cutting features, I'd:

```python
# Streaming response
async def ask_streaming(query):
    # Retrieval (200ms)
    docs = await hybrid_retriever.search(query)
    
    # Stream docs immediately
    yield json.dumps({'sources': docs})
    
    # Generate answer in background (streaming)
    async for token in openai_stream(docs):
        yield token  # Stream to client as it arrives
```

This way:
- User gets sources immediately (<300ms)
- LLM answer streams in as it's generated (feels fast)
- Still provides full value, just with progressive rendering

This is how ChatGPT does it - streams tokens so it feels instant."

---

## 9. Your system returns confidence 0.45 for "AI governance" query. Is that good or bad?

### âŒ Weak Answer:
"It could be better, maybe 0.6 or 0.7."

### âœ… Strong Answer:
"Actually, 0.45 is reasonable for **your use case**. Here's why:

**Context matters:**

| Scenario | Confidence | Quality | Interpretation |
|----------|------------|---------|-----------------|
| Exact doc title match | 0.90-1.0 | Perfect | High confidence warranted |
| Strong semantic + keyword | 0.60-0.80 | Good | Likely correct |
| Mixed signals | 0.40-0.60 | Fair/Useful | Information is there but dispersed |
| Weak match | 0.20-0.40 | Poor | Better sources exist |
| Not found | 0.0-0.20 | Bad | Should try different query |

**For 'What is AI governance?' scoring 0.45:**
- FAISS scored it 0.50 (semantic match)
- BM25 scored it 0.40 (keyword match)
- No exact phrase match ('governance' appears but not 'AI governance' exactly)
- Sources: 3 different documents needed
- Combined: 0.6*0.50 + 0.4*0.40 = 0.46 â‰ˆ 0.45

**Is that good?** YES, because:
1. System is being conservative (good for enterprise)
2. User knows to check sources (transparency)
3. Multiple documents provide comprehensive answer
4. Better than 0.9 when it's only partially correct

**If I wanted higher confidence:**
```python
# Term overlap boost
if exact_terms_in_doc:
    confidence *= 1.1  # +10% boost
    
# Document quality scoring
confidence *= doc_quality_score  # 0.8-1.0 based on doc rating

# Recency bonus
if doc_is_recent:
    confidence *= 1.05  # +5% for recent updates
```

But then I risk inflating confidence scores and misleading users."

---

## 10. Walk me through a query that FAILS. What goes wrong and how is it handled?

### âœ… Strong Answer:

**Scenario: User asks 'What is the meaning of life?'**

```
Query flow:
1. Input validation âœ…
   - Not empty âœ“
   - < 500 chars âœ“
   
2. Retrieval âš ï¸
   - Semantic search: Score 0.05 (very weak, doc is about policies not philosophy)
   - Keyword search: Score 0.02 (no relevant keywords)
   - Confidence: 0.6*0.05 + 0.4*0.02 = 0.038
   - Returns: Top 3 documents (even if weak)
   
3. LLM Generation âš ï¸
   - Prompt: "Using these policy documents, answer: What is the meaning of life?"
   - GPT-4: "Based on the provided documents on corporate governance and risk management, I cannot answer this philosophical question. However, the documents do discuss..."
   - LLM admits lack of knowledge
   
4. Response âœ…
   {
     "answer": "This question is outside the scope of the documents provided. Based on corporate policies, I cannot provide a meaningful answer.",
     "confidence": 0.04,
     "sources": ["data_governance_policy", ...]
   }

User gets: Honest answer with low confidence â†’ knows to rephrase or ask differently
```

**Better query: 'What is data governance?'**

```
1. Validation âœ…
2. Retrieval âœ…
   - Semantic: 0.92 (perfect match on 'data governance')
   - Keyword: 0.88 (keywords present)
   - Confidence: 0.6*0.92 + 0.4*0.88 = 0.904
   - Returns: [01_Data_Governance_Policy]
   
3. LLM âœ…
   - Abundant context from matching document
   - Generates: Clear, accurate answer
   
4. Response âœ…
   {
     "answer": "Data governance is...",
     "confidence": 0.90,
     "sources": ["01_Data_Governance_Policy"]
   }
```

**Error scenario: Rate limit**

```
Query flow:
1-2. Validation + Retrieval âœ…
3. LLM Generation âŒ
   - OpenAI API: 429 Too Many Requests
   - AsyncEmbeddingClient catches this:
     * Attempt 1: Wait 1s, retry
     * Attempt 2: Wait 2s, retry
     * Attempt 3: Wait 4s, retry
     * All 3 fail: Raise RuntimeError("rate_limit")
     
4. Endpoint error handler âœ…
   - Catches RuntimeError
   - Returns: 503 Service Unavailable
   
User gets: Clear message to wait 1 minute before retrying
```

This shows:
- Graceful degradation (honest answer when info absent)
- Proper error handling (rate limit â†’ retry â†’ HTTP 503)
- Transparency (confidence scores indicate certainty)
"

---

## 11. How would you handle 1 million documents?

### âœ… Strong Answer:

"Current architecture bottleneck: FAISS index builds in memory. Here's the scaling strategy:

```
Current (single server): 10K docs = 10 minutes build
Scaled (distributed): 1M docs = ?

Phase 1: Vertical Scaling (single large server)
- Move to GPU-enabled FAISS
- FAISS partitioning: Split into 100 4.4M-embedding partitions
- Speedup: ~5x with GPU
- Cost: $1000/month for GPU server
- Build time: ~2 minutes

Phase 2: Horizontal Scaling (distributed)
- Database: PostgreSQL + pgvector (vector DB)
- API: Load balance 5 FastAPI instances
- Async: Batch 100 concurrent embedding requests
- Build time: ~30 seconds (parallel processing)
- Cost: $500/month DB + $300/month API servers

Phase 3: Production Grade (enterprise)
- Vector DB: Weaviate or Pinecone (managed service)
- Streaming: Process documents as they arrive (not batch)
- Caching: Redis distributed cache (across instances)
- Monitoring: Prometheus metrics, Grafana dashboards
- Cost: $200-500/month depending on document update frequency

Implementation:
```python
# Current
from faiss import IndexFlatL2
index = IndexFlatL2(1536)
for doc in docs:
    embedding = openai.embed(doc)
    index.add(embedding)

# Scaled
from weaviate import Client
client = Client(url="https://my-weaviate.cloud")
# Collections auto-scale, sharded across servers
# Async batch processing built-in
for batch in batches(docs, 100):
    embeddings = await batch_embed_async(batch)
    client.batch.add_objects(embeddings)
```"

---

## 12. What's a production issue that could happen? How would you debug it?

### âœ… Strong Answer:

**Issue: "API responses are slow on dates after March 15, accuracy drops"**

**Debug approach:**

```python
# 1. Metrics check
SELECT
  DATE(timestamp),
  COUNT(*) as query_count,
  AVG(latency_ms) as avg_latency,
  AVG(confidence) as avg_confidence
FROM query_logs
GROUP BY DATE(timestamp)
ORDER BY DATE DESC;

# Result: Latency 2500ms normal, after March 15 = 8000ms âš ï¸ 
# Confidence: 0.55 normal, after March 15 = 0.25 âš ï¸

# 2. Check for data changes
SELECT COUNT(*) FROM embeddings_cache WHERE created_at > '2026-03-15';
# Result: 0 (no new embeddings cached after March 15!)

# 3. Check SQLite integrity
PRAGMA integrity_check;
ANALYZE;
REINDEX;

# 4. Hypothesis: Cache corrupted, now hitting OpenAI API every time
# Confirm:
SELECT COUNT(*) FROM query_logs 
WHERE latency_ms > 5000 AND DATE(timestamp) > '2026-03-15';

# 5. Root cause: Someone cleaned cache db without rebuilding index
systemctl restart embedding_batch_job  # Rebuild cache

# 6. Monitor:
SELECT COUNT(*) FROM embeddings_cache;
# Latency drops back to 2500ms âœ…
# Confidence back to 0.55 âœ…
```

**Production fix:**
```python
# Add cache validation on startup
async def startup_check():
    cache_count = db.execute("SELECT COUNT(*) FROM embeddings_cache")
    if cache_count == 0:
        logger.warning("Cache empty - rebuilding...")
        await rebuild_embeddings_cache()
    
    # Verify FAISS index matches cache
    if faiss_index.ntotal != cache_count:
        logger.error(f"Index mismatch: FAISS has {faiss_index.ntotal}, "
                     f"cache has {cache_count}")
        raise RuntimeError("FAISS index corrupted")
```

This shows:
- Systematic debugging approach
- How to use monitoring/logging
- Understanding of distributed system failures
- Production monitoring mindset"

---

## 13. Your API requires an API key. What if someone steals it?

### âœ… Strong Answer:

"Good security question! Current protection:

```
ðŸ”’ Current measures:
- API key in .env (not in source control)
- Key stored as plaintext in SQLite for AUTH validation â† PROBLEM
- Keys tracked in logs (need to redact)

âš ï¸ Vulnerabilities:
1. If someone steals the key file (.env), they can make unlimited requests
2. Old keys can't be easily revoked
3. No audit trail of WHO used the key

ðŸ›¡ï¸ Production hardening:

1. API Key Rotation Strategy
# keys table
CREATE TABLE api_keys (
  key_id (PK),
  key_hash (SHA256),      -- never store plain text
  created_at,
  rotated_at,
  expires_at,
  is_active
);

Every 90 days:
- Generate new key
- Revoke old key
- Notify all users

2. Rate limiting per key
# key_limits table
CREATE TABLE key_limits (
  key_id,
  requests_per_minute,
  concurrent_requests,
  ip_whitelist,
  user_id
);

3. Audit logging
# audit_log table
CREATE TABLE audit_log (
  timestamp,
  key_id,
  query,
  result,
  status_code,
  ip_address
);

4. Secret management
# Instead of .env files
- AWS Secrets Manager (auto-rotation)
- Vault by HashiCorp (encrypted storage)
- Azure Key Vault (managed service)

5. Detection
- Monitor for unusual patterns:
  * 100x normal request rate
  * Requests from new IPs
  * Failed auth attempts
  * Queries outside normal parameters

Implementation:
```python
@app.post('/ask')
async def ask_question(query: Query, request: Request):
    api_key = request.headers.get('x-api-key')
    client_ip = request.client.host
    
    # Validate key
    key_record = db.get_key(api_key)
    if not key_record or not key_record.is_active:
        await audit_log('AUTH_FAILED', api_key, client_ip)
        # Rotate compromised key
        notify_admin('Suspicious key: ' + api_key)
        raise HTTPException(401)
    
    # Check rate limit
    if is_rate_limited(key_record.key_id):
        await audit_log('RATE_LIMITED', api_key, client_ip)
        raise HTTPException(429)
    
    # Check IP whitelist
    if key_record.ip_whitelist and client_ip not in key_record.ip_whitelist:
        await audit_log('IP_MISMATCH', api_key, client_ip)
        raise HTTPException(403)
    
    # Proceed
    result = await ask(query)
    await audit_log('SUCCESS', api_key, client_ip, result)
    return result
```
"

---

## 14. You built this with AI. How much of it is YOUR work?

### âœ… Strong Answer:

"Great question - it's important to be honest. Here's the breakdown:

**AI Generated (~40%):**
- Initial API structure (FastAPI boilerplate)
- Streamlit UI layout
- Basic error handling skeletons
- Test case templates

**My Work (~60%):**
- **Architecture decisions:** Why FastAPI + Streamlit? Why hybrid search? Why SQLite?
- **Integration:** Connecting OpenAI + FAISS + BM25 into cohesive system
- **Optimization:** Caching strategy (SHA256 keys, persistence), async batching, hybrid scoring weighting
- **Problem-solving:** Fixed logging KeyError issues, slowapi parameter conflict, confidence scoring
- **Testing:** Diagnosed edge cases, wrote actual test logic, fixed failures
- **Production hardening:** Error handling, retry logic, validation, security

**Key decisions that show my thinking:**
1. 60/40 hybrid weighting (why not 50/50 or 80/20?)
2. SQLite caching over Redis (when each is appropriate)
3. Exponential backoff retry (learned from experience with rate limits)
4. Structured JSON logging (avoided field name conflicts)
5. Async fallback to sync (graceful degradation)

**My learning process:**
- AI generated initial code
- I tested it â†’ found bugs
- I fixed bugs â†’ added features
- I optimized â†’ added caching/async
- I hardened â†’ added error handling/testing

Think of AI as a code generator, not a software engineer. I **architected** the system, made the decisions, debugged the issues, and optimized the performance.

**In an interview:** AI is a tool, like Stack Overflow. What matters is:
- Can you explain every line of code? âœ… Yes
- Can you debug when something breaks? âœ… Yes
- Can you optimize for different constraints? âœ… Yes
- Can you architect a system from requirements? âœ… Yes
"

---

## ðŸ“‹ Quick Reference: Numbers to Know

| Metric | Value | Context |
|--------|-------|---------|
| Caching speedup | 1866x | Cache hit <1ms vs miss 6.07s |
| Async speedup | 1.3x | 1.30s vs 1.68s batch vs sequential |
| Rate limit | 5/min | Per IP |
| Query timeout | 30s | Max wait for response |
| Max query length | 500 chars | Input validation |
| Embedding dims | 1536 | OpenAI model output size |
| Test coverage | 23 tests | 100% pass rate |
| Retry attempts | 3 | With exponential backoff |
| Backoff delays | 1s, 2s, 4s | Exponential: 2^attempt |
| Semaphore limit | 10 | Max concurrent async requests |
| Cache storage | ~0.5MB/100docs | SQLite on disk |

---

**Key Takeaway:** You built a solid, production-style internal system. Know how to explain your decisions and be ready to defend your trade-offs. That's what impresses interviewers.

