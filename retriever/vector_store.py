import os
import asyncio
import faiss
import json
import numpy as np
from openai import OpenAI
from config.settings import OPENAI_API_KEY, EMBEDDING_MODEL
from api.cache import embeddings_cache
from llm.async_client import AsyncEmbeddingClient


class VectorStore:

    def __init__(self, index_path="vector_store"):
        self.index = None
        self.documents = []
        self.index_path = index_path
        self.client = OpenAI(api_key=OPENAI_API_KEY)  # Fallback for sync
        self.async_client = AsyncEmbeddingClient()
        self.cache_hits = 0
        self.cache_misses = 0

        # Ensure directory exists
        os.makedirs(self.index_path, exist_ok=True)

    def embed(self, text):
        """Synchronous embed for single texts (uses cache)."""
        # Check cache first
        cached_embedding = embeddings_cache.get(text, model=EMBEDDING_MODEL)
        if cached_embedding is not None:
            self.cache_hits += 1
            return cached_embedding
        
        # Cache miss: call OpenAI with error handling
        self.cache_misses += 1
        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            embedding = np.array(response.data[0].embedding).astype("float32")
            
            # Store in cache for future use
            embeddings_cache.set(text, embedding, model=EMBEDDING_MODEL)
            
            return embedding
        except Exception as e:
            raise RuntimeError(f"Failed to embed text: {str(e)}")

    async def embed_batch_async(self, texts):
        """
        Asynchronously embed multiple texts with caching.
        Uses concurrent httpx requests for speed.
        """
        embeddings = []
        to_fetch = []
        to_fetch_indices = []
        
        # Check cache for all texts
        for i, text in enumerate(texts):
            cached = embeddings_cache.get(text, model=EMBEDDING_MODEL)
            if cached is not None:
                self.cache_hits += 1
                embeddings.append(cached)
            else:
                self.cache_misses += 1
                to_fetch.append(text)
                to_fetch_indices.append(i)
        
        # Fetch non-cached texts concurrently
        if to_fetch:
            fetched = await self.async_client.embed_batch(to_fetch, max_concurrent=10)
            for text, embedding in zip(to_fetch, fetched):
                embeddings_cache.set(text, embedding, model=EMBEDDING_MODEL)
        else:
            fetched = []

        # Reconstruct in original order
        to_fetch_set = set(to_fetch_indices)
        result = [None] * len(texts)
        cache_idx = 0
        fetch_idx = 0
        for i in range(len(texts)):
            if i in to_fetch_set:
                result[i] = fetched[fetch_idx]
                fetch_idx += 1
            else:
                result[i] = embeddings[cache_idx]
                cache_idx += 1
        
        return result

    def build_index(self, documents):
        print("Generating embeddings...")

        self.documents = documents
        embeddings = []

        for doc in documents:
            vector = self.embed(doc["content"])
            embeddings.append(vector)

        embeddings = np.vstack(embeddings)

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

        cache_stats = embeddings_cache.get_stats()
        print(f"FAISS index built successfully.")
        print(f"Embeddings Cache: {cache_stats['cached_embeddings']} cached | " +
              f"Size: {cache_stats['db_size_mb']}MB | " +
              f"Hits: {self.cache_hits} | Misses: {self.cache_misses}")

    async def build_index_async(self, documents):
        """Async batch embed + build FAISS index."""
        print("Generating embeddings (async batch mode)...")

        self.documents = documents
        texts = [doc["content"] for doc in documents]
        
        # Batch embed all texts concurrently
        embeddings = await self.embed_batch_async(texts)
        
        embeddings_array = np.vstack(embeddings)

        dimension = embeddings_array.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings_array)

        cache_stats = embeddings_cache.get_stats()
        print(f"FAISS index built successfully (async mode).")
        print(f"Embeddings Cache: {cache_stats['cached_embeddings']} cached | " +
              f"Size: {cache_stats['db_size_mb']}MB | " +
              f"Hits: {self.cache_hits} | Misses: {self.cache_misses}")

    def save(self):
        if self.index is None:
            raise ValueError("Index not built yet.")

        faiss.write_index(self.index, os.path.join(self.index_path, "index.faiss"))

        with open(os.path.join(self.index_path, "metadata.json"), "w") as f:
            json.dump(self.documents, f)

        print("Index and metadata saved to disk.")

    def load(self):
        index_file = os.path.join(self.index_path, "index.faiss")
        metadata_file = os.path.join(self.index_path, "metadata.json")

        if not os.path.exists(index_file) or not os.path.exists(metadata_file):
            raise FileNotFoundError("Saved index not found.")

        self.index = faiss.read_index(index_file)

        with open(metadata_file, "r") as f:
            self.documents = json.load(f)

        print("Index loaded successfully from disk.")

    def search(self, query, k=4):
        if self.index is None:
            raise ValueError("Index not loaded or built.")

        query_vector = self.embed(query).reshape(1, -1)

        distances, indices = self.index.search(query_vector, k)

        # Convert distances to similarity scores (inverse)
        # FAISS L2 distance: lower = more similar
        # Normalize to 0-1 range
        max_distance = distances[0].max() + 1e-6
        similarities = 1.0 - (distances[0] / max_distance)

        results = []
        for i, idx in enumerate(indices[0]):
            doc = self.documents[idx].copy()
            doc["vector_score"] = float(similarities[i])
            results.append(doc)

        return results
