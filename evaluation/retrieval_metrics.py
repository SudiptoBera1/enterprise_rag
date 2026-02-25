import json
import math
from pathlib import Path


def precision_at_k(retrieved_ids, relevant_ids, k):
    top_k = retrieved_ids[:k]
    if k <= 0:
        return 0.0
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / k


def recall_at_k(retrieved_ids, relevant_ids, k):
    if not relevant_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / len(relevant_ids)


def mrr(retrieved_ids, relevant_ids):
    for idx, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_ids:
            return 1.0 / idx
    return 0.0


def ndcg_at_k(retrieved_ids, relevant_ids, k):
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids[:k], start=1):
        rel = 1.0 if doc_id in relevant_ids else 0.0
        dcg += rel / math.log2(i + 1)

    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    if idcg == 0:
        return 0.0
    return dcg / idcg


def load_sample_dataset(path="evaluation/sample_retrieval_dataset.json"):
    dataset_path = Path(path)
    if not dataset_path.exists():
        return []
    with dataset_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_retriever(hybrid_retriever, dataset, k=3):
    if not dataset:
        return {
            "dataset_size": 0,
            "precision_at_k": 0.0,
            "recall_at_k": 0.0,
            "mrr": 0.0,
            "ndcg_at_k": 0.0,
        }

    precision_scores = []
    recall_scores = []
    mrr_scores = []
    ndcg_scores = []

    for item in dataset:
        query = item.get("query", "")
        relevant_ids = set(item.get("relevant_doc_ids", []))
        results = hybrid_retriever.retrieve(query, k=k)
        retrieved_ids = [doc.get("doc_id") for doc in results]

        precision_scores.append(precision_at_k(retrieved_ids, relevant_ids, k))
        recall_scores.append(recall_at_k(retrieved_ids, relevant_ids, k))
        mrr_scores.append(mrr(retrieved_ids, relevant_ids))
        ndcg_scores.append(ndcg_at_k(retrieved_ids, relevant_ids, k))

    n = len(dataset)
    return {
        "dataset_size": n,
        "precision_at_k": round(sum(precision_scores) / n, 4),
        "recall_at_k": round(sum(recall_scores) / n, 4),
        "mrr": round(sum(mrr_scores) / n, 4),
        "ndcg_at_k": round(sum(ndcg_scores) / n, 4),
        "k": k,
    }
