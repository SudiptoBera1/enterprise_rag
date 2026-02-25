from ingestion.loader import load_documents
from retriever.vector_store import VectorStore
from retriever.keyword_search import KeywordSearch
from retriever.hybrid import HybridRetriever
from llm.prompt import build_prompt
from llm.generator import generate_response, generate_response_async
from api.exceptions import InitializationError
import asyncio
import re
import time


class RAGService:

    def __init__(self):
        # Lightweight initialization: defer heavy work until first request
        print("Initializing RAG service (lazy).")
        self.initialized = False
        self.documents = []
        self.vector_store = None
        self.keyword_search = None
        self.hybrid = None
        self._init_lock = asyncio.Lock()
        self.init_error = None
        self._stopwords = {
            "the", "a", "an", "is", "are", "to", "of", "in", "on", "for", "and",
            "or", "with", "what", "how", "why", "when", "where", "which", "who",
            "by", "from", "as", "at", "it", "this", "that", "be", "about"
        }

    def _extract_terms(self, text: str):
        terms = re.findall(r"[a-zA-Z0-9_]+", (text or "").lower())
        return {t for t in terms if len(t) > 2 and t not in self._stopwords}

    def _normalize_answer_citations(self, answer: str, sources):
        if not answer:
            return answer

        normalized = answer
        # Normalize bracket citation style to parenthesis style.
        normalized = re.sub(r"\[Source:\s*([^\]]+)\]", r"(Source: \1)", normalized, flags=re.IGNORECASE)
        # Ensure one space after colon for parenthesis style.
        normalized = re.sub(r"\(Source:\s*([^)]+)\)", r"(Source: \1)", normalized, flags=re.IGNORECASE)

        if "insufficient information in provided documents." in normalized.lower():
            return normalized

        has_citation = re.search(r"\(Source:\s*[^)]+\)", normalized, flags=re.IGNORECASE) is not None
        if not has_citation and sources:
            normalized = normalized.rstrip() + f" (Source: {sources[0]})"

        return normalized

    def calculate_confidence(self, query, contexts, answer):
        """
        Calculate confidence with retrieval quality + query coverage + citation adherence.
        """
        if not contexts:
            return 0.0

        scores = [max(0.0, min(1.0, float(doc.get("relevance_score", 0.0)))) for doc in contexts]
        avg_retrieval = sum(scores) / len(scores)
        top_retrieval = max(scores)

        query_terms = self._extract_terms(query)
        context_text = " ".join(doc.get("content", "") for doc in contexts)
        context_terms = self._extract_terms(context_text)
        coverage = 1.0 if not query_terms else (len(query_terms.intersection(context_terms)) / len(query_terms))

        has_citation = re.search(r"\(Source:\s*[^)]+\)", answer or "", flags=re.IGNORECASE) is not None
        citation_component = 1.0 if has_citation else 0.5

        # Weighted calibration tuned for interview demo consistency.
        confidence = (
            0.45 * avg_retrieval
            + 0.25 * top_retrieval
            + 0.20 * coverage
            + 0.10 * citation_component
        )
        return round(max(0.0, min(1.0, confidence)), 2)

    def _build_result(self, query, contexts, answer, telemetry=None):
        sources = list(dict.fromkeys(doc["doc_id"] for doc in contexts))
        answer = self._normalize_answer_citations(answer, sources)
        confidence = self.calculate_confidence(query, contexts, answer)
        result = {
            "answer": answer,
            "sources": sources,
            "confidence": confidence
        }
        if telemetry:
            result["_telemetry"] = telemetry
        return result

    def _filter_contexts_by_allowed_docs(self, contexts, allowed_doc_ids=None):
        if allowed_doc_ids is None:
            return contexts
        allowed_set = set(allowed_doc_ids)
        return [ctx for ctx in contexts if ctx.get("doc_id") in allowed_set]

    def ask(self, query: str, allowed_doc_ids=None):
        # Ensure the heavy components are built on first use
        # Run async initialization synchronously if needed
        if not self.initialized:
            asyncio.run(self.ensure_initialized_async())

        retrieval_start = time.perf_counter()
        contexts = self.hybrid.retrieve(query, k=3)
        contexts = self._filter_contexts_by_allowed_docs(contexts, allowed_doc_ids)
        retrieval_ms = int((time.perf_counter() - retrieval_start) * 1000)

        prompt = build_prompt(query, contexts)
        generation_start = time.perf_counter()
        llm_result = generate_response(prompt)
        generation_ms = int((time.perf_counter() - generation_start) * 1000)

        if isinstance(llm_result, dict):
            answer = llm_result.get("content", "")
            token_usage = llm_result.get("usage", {})
        else:
            answer = llm_result
            token_usage = {}

        telemetry = {
            "retrieval_ms": retrieval_ms,
            "generation_ms": generation_ms,
            "token_usage": token_usage,
        }
        return self._build_result(query, contexts, answer, telemetry=telemetry)

    async def ask_async(self, query: str, allowed_doc_ids=None):
        """Async version of ask() for use in async endpoints."""
        # Ensure the heavy components are built on first use
        await self.ensure_initialized_async()

        retrieval_start = asyncio.get_running_loop().time()
        contexts = self.hybrid.retrieve(query, k=3)
        contexts = self._filter_contexts_by_allowed_docs(contexts, allowed_doc_ids)
        retrieval_ms = int((asyncio.get_running_loop().time() - retrieval_start) * 1000)

        prompt = build_prompt(query, contexts)
        generation_start = asyncio.get_running_loop().time()
        llm_result = await generate_response_async(prompt)
        generation_ms = int((asyncio.get_running_loop().time() - generation_start) * 1000)

        if isinstance(llm_result, dict):
            answer = llm_result.get("content", "")
            token_usage = llm_result.get("usage", {})
        else:
            answer = llm_result
            token_usage = {}

        telemetry = {
            "retrieval_ms": retrieval_ms,
            "generation_ms": generation_ms,
            "token_usage": token_usage,
        }
        return self._build_result(query, contexts, answer, telemetry=telemetry)

    async def ensure_initialized_async(self):
        """Build documents, vector store and keyword index asynchronously on first use."""
        if self.initialized:
            return

        async with self._init_lock:
            if self.initialized:
                return

            print("RAGService: performing first-time initialization (async mode, loading documents, building indices)...")
            
            try:
                self.documents = load_documents("data/raw")

                # If there are no documents, raise a clear InitializationError
                if not self.documents:
                    raise InitializationError(details="No documents found in data/raw. Add PDFs to populate the index.")

                self.vector_store = VectorStore()
                
                try:
                    # Try async build with retry
                    await self.vector_store.build_index_async(self.documents)
                except RuntimeError as e:
                    # Fallback to sync if async fails
                    print(f"Async initialization failed, falling back to sync: {e}")
                    self.vector_store.build_index(self.documents)
                
                self.vector_store.save()
                self.vector_store.load()

                self.keyword_search = KeywordSearch(self.documents)
                self.hybrid = HybridRetriever(self.vector_store, self.keyword_search)

                self.initialized = True
                self.init_error = None
                print("RAGService: initialization complete (async mode).")
                
            except InitializationError:
                self.init_error = "RAG initialization failed."
                raise
            except Exception as e:
                print(f"Initialization error: {e}")
                self.init_error = str(e)
                raise InitializationError(details=f"Failed to initialize RAG system: {str(e)}")

    def ensure_initialized(self):
        """Build documents, vector store and keyword index on first use (sync fallback)."""
        if self.initialized:
            return

        print("RAGService: performing first-time initialization (sync mode, loading documents, building indices)...")
        self.documents = load_documents("data/raw")

        # If there are no documents, raise a clear InitializationError
        if not self.documents:
            raise InitializationError(details="No documents found in data/raw. Add PDFs to populate the index.")

        self.vector_store = VectorStore()
        # Only build if there are documents
        self.vector_store.build_index(self.documents)
        self.vector_store.save()
        self.vector_store.load()

        self.keyword_search = KeywordSearch(self.documents)
        self.hybrid = HybridRetriever(self.vector_store, self.keyword_search)

        self.initialized = True
        self.init_error = None
        print("RAGService: initialization complete (sync mode).")

    def is_initialized(self):
        """Return whether the RAG indices have been initialized."""
        return bool(self.initialized)

    def get_health(self):
        """Return initialization state for health checks."""
        return {
            "rag_initialized": self.is_initialized(),
            "init_error": self.init_error
        }


# Module-level singleton so routers and health checks can import it
rag_service = RAGService()
