import sqlite3
import json
import hashlib
import os
from typing import Optional, List
import numpy as np


class EmbeddingsCache:
    """
    SQLite-backed cache for embeddings.
    Stores: text_hash -> embedding vector + metadata
    Persists across restarts; avoids redundant OpenAI calls.
    """

    def __init__(self, db_path: str = "vector_store/embeddings_cache.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    text_hash TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_text_hash ON embeddings(text_hash)
            """)
            conn.commit()

    def _hash_text(self, text: str) -> str:
        """Generate a SHA256 hash of the text."""
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str, model: str = "text-embedding-3-small") -> Optional[np.ndarray]:
        """
        Retrieve embedding from cache if exists.
        Returns numpy array or None if not cached.
        """
        text_hash = self._hash_text(text)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT embedding, model FROM embeddings WHERE text_hash = ?",
                (text_hash,)
            ).fetchone()
        
        if row and row[1] == model:
            # Deserialize embedding from JSON
            embedding = np.array(json.loads(row[0]), dtype="float32")
            return embedding
        
        return None

    def set(self, text: str, embedding: np.ndarray, model: str = "text-embedding-3-small") -> None:
        """
        Store embedding in cache.
        """
        text_hash = self._hash_text(text)
        embedding_json = json.dumps(embedding.tolist())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO embeddings (text_hash, text, embedding, model)
                VALUES (?, ?, ?, ?)
                """,
                (text_hash, text, embedding_json, model)
            )
            conn.commit()

    def get_stats(self) -> dict:
        """Return cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
            db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
        
        return {
            "cached_embeddings": count,
            "db_size_mb": round(db_size_mb, 2)
        }

    def clear(self) -> None:
        """Clear all cached embeddings."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM embeddings")
            conn.commit()


# Module-level singleton
embeddings_cache = EmbeddingsCache()
