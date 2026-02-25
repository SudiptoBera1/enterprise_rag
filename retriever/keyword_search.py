from rank_bm25 import BM25Okapi


class KeywordSearch:

    def __init__(self, documents):
        self.documents = documents
        self.tokenized_docs = [
            doc["content"].split() for doc in documents
        ]
        self.bm25 = BM25Okapi(self.tokenized_docs)

    def search(self, query, k=4):
        tokenized_query = query.split()
        scores = self.bm25.get_scores(tokenized_query)

        # Get top k indices
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:k]

        # Normalize BM25 scores to 0-1 range
        max_score = max(scores) + 1e-6 if scores.size > 0 else 1.0
        normalized_scores = scores / max_score

        results = []
        for idx in top_indices:
            doc = self.documents[idx].copy()
            doc["keyword_score"] = float(normalized_scores[idx])
            results.append(doc)
        
        return results