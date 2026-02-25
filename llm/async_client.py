import asyncio
import httpx
import json
import numpy as np
from typing import List
import time
from config.settings import OPENAI_API_KEY, EMBEDDING_MODEL


class EmbeddingClientError(RuntimeError):
    """Base error for async embedding failures."""


class EmbeddingRateLimitError(EmbeddingClientError):
    """Raised when OpenAI embeddings API is rate limited."""


class EmbeddingTimeoutError(EmbeddingClientError):
    """Raised on timeout/connectivity failure after retries."""


class EmbeddingAPIError(EmbeddingClientError):
    """Raised for non-rate-limit OpenAI API failures."""


class AsyncEmbeddingClient:
    """
    Async OpenAI embeddings client using httpx.
    Supports concurrent embedding requests with retry logic.
    """

    def __init__(self, api_key: str = OPENAI_API_KEY, model: str = EMBEDDING_MODEL):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        self.max_retries = 3
        self.retry_delay = 1.0  # Start with 1 second

    async def embed_single(self, text: str, client: httpx.AsyncClient) -> np.ndarray:
        """Embed a single text string using httpx with retry logic."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "input": text
        }
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    json=payload,
                    headers=headers,
                    timeout=60.0
                )
                response.raise_for_status()
                
                data = response.json()
                embedding = np.array(data["data"][0]["embedding"], dtype="float32")
                return embedding
                
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Timeout/connection error, retrying in {delay}s... (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                else:
                    raise EmbeddingTimeoutError(
                        f"Embedding timed out/connection failed after {self.max_retries} attempts: {e}"
                    )
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delay * (2 ** attempt)
                        print(f"Rate limited, retrying in {delay}s...")
                        await asyncio.sleep(delay)
                    else:
                        raise EmbeddingRateLimitError(
                            f"Embedding API rate limited after {self.max_retries} attempts"
                        )
                else:
                    raise EmbeddingAPIError(
                        f"OpenAI embeddings API error {e.response.status_code}: {e.response.text}"
                    )
                    
            except EmbeddingClientError:
                raise
            except Exception as e:
                raise EmbeddingClientError(f"Unexpected embedding error: {str(e)}")
        
        raise EmbeddingClientError(f"Failed to embed after {self.max_retries} attempts")

    async def embed_batch(self, texts: List[str], max_concurrent: int = 10) -> List[np.ndarray]:
        """
        Embed multiple texts concurrently with retry logic.
        
        Args:
            texts: List of strings to embed
            max_concurrent: Max concurrent requests
        
        Returns:
            List of embedding vectors (float32 numpy arrays)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def embed_with_semaphore(text: str, client: httpx.AsyncClient) -> np.ndarray:
            async with semaphore:
                return await self.embed_single(text, client)
        
        async with httpx.AsyncClient() as client:
            tasks = [embed_with_semaphore(text, client) for text in texts]
            try:
                embeddings = await asyncio.gather(*tasks)
                return embeddings
            except EmbeddingClientError:
                raise
            except Exception as e:
                raise EmbeddingClientError(f"Batch embedding failed: {str(e)}")
