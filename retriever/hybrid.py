class HybridRetriever:

    def __init__(self, vector_store, keyword_search, vector_weight=0.6, keyword_weight=0.4):
        self.vector_store = vector_store
        self.keyword_search = keyword_search
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    def retrieve(self, query, k=4):
        """
        Retrieve documents using hybrid scoring (semantic + keyword).
        
        Returns documents with combined relevance scores.
        """
        # Get vector results with similarity scores
        vector_results = self.vector_store.search(query, k)

        # Get keyword results with BM25 scores
        keyword_results = self.keyword_search.search(query, k)

        # Build score map: content -> combined score
        score_map = {}
        seen_content = {}

        # Add vector scores
        for doc in vector_results:
            content = doc["content"]
            if content not in seen_content:
                seen_content[content] = doc.copy()
                score_map[content] = self.vector_weight * doc.get("vector_score", 0)
            else:
                # Update if we already saw this content, take max
                score_map[content] = max(score_map[content], self.vector_weight * doc.get("vector_score", 0))

        # Add keyword scores
        for doc in keyword_results:
            content = doc["content"]
            if content in score_map:
                # Combine scores
                score_map[content] += self.keyword_weight * doc.get("keyword_score", 0)
            else:
                seen_content[content] = doc.copy()
                score_map[content] = self.keyword_weight * doc.get("keyword_score", 0)

        # Sort by combined score
        sorted_results = sorted(
            seen_content.items(),
            key=lambda x: score_map[x[0]],
            reverse=True
        )[:k]

        # Attach final scores
        results = []
        for content, doc in sorted_results:
            doc["relevance_score"] = round(score_map[content], 3)
            results.append(doc)

        return results