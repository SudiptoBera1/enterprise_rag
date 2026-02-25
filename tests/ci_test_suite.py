import asyncio
import httpx
from unittest.mock import MagicMock, patch, AsyncMock

from api.auth import get_current_user
from api.service import RAGService
from llm.async_client import AsyncEmbeddingClient


VALID_API_KEY = "test-api-key"
INVALID_API_KEY = "wrongkey"
VALID_QUERY = "What is AI governance?"
EMPTY_QUERY = ""
LONG_QUERY = "What " * 200


def test_empty_query_rejected(client):
    resp = client.post("/ask", json={"query": EMPTY_QUERY}, headers={"x-api-key": VALID_API_KEY})
    assert resp.status_code == 400
    assert resp.json()["error"] == "INVALID_REQUEST"


def test_query_too_long_rejected(client):
    resp = client.post("/ask", json={"query": LONG_QUERY}, headers={"x-api-key": VALID_API_KEY})
    assert resp.status_code == 400
    assert resp.json()["error"] == "INVALID_REQUEST"


def test_missing_api_key(client):
    resp = client.post("/ask", json={"query": VALID_QUERY})
    assert resp.status_code == 401


def test_invalid_api_key(client):
    resp = client.post("/ask", json={"query": VALID_QUERY}, headers={"x-api-key": INVALID_API_KEY})
    assert resp.status_code == 401


def test_boundary_query_length(client):
    boundary_query = "a" * 500
    resp = client.post("/ask", json={"query": boundary_query}, headers={"x-api-key": VALID_API_KEY})
    assert resp.status_code != 400 or "too long" not in resp.json().get("details", "").lower()


def test_health_check_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "rag_initialized" in data
    assert "init_error" in data


def test_health_check_no_auth_required(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_valid_query_returns_200(client):
    resp = client.post("/ask", json={"query": VALID_QUERY}, headers={"x-api-key": VALID_API_KEY})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["answer"], str)
    assert isinstance(data["confidence"], (int, float))
    assert isinstance(data["sources"], list)
    assert "latency_ms" in data


def test_response_contains_valid_sources(client):
    resp = client.post("/ask", json={"query": VALID_QUERY}, headers={"x-api-key": VALID_API_KEY})
    assert resp.status_code == 200
    data = resp.json()
    expected_sources = {
        "01_Data_Governance_Policy",
        "07_AI_Governance_Policy",
        "09_AI_Model_Validation_SOP",
    }
    for source in data["sources"]:
        assert source in expected_sources


@patch("llm.async_client.httpx.AsyncClient.post")
def test_retry_on_rate_limit(mock_post):
    request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
    rate_limited = httpx.Response(429, request=request)

    success_response = MagicMock()
    success_response.raise_for_status.return_value = None
    success_response.json.return_value = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    mock_post.side_effect = [
        httpx.HTTPStatusError("rate limited", request=request, response=rate_limited),
        httpx.HTTPStatusError("rate limited", request=request, response=rate_limited),
        success_response,
    ]

    async def run_test():
        async with httpx.AsyncClient() as http_client:
            client = AsyncEmbeddingClient(api_key="test-key")
            embedding = await client.embed_single("test text", http_client)
            assert embedding.shape[0] == 3

    asyncio.run(run_test())
    assert mock_post.call_count == 3


@patch("llm.async_client.httpx.AsyncClient.post")
def test_retry_on_temporary_timeout(mock_post):
    success_response = MagicMock()
    success_response.raise_for_status.return_value = None
    success_response.json.return_value = {"data": [{"embedding": [0.4, 0.5, 0.6]}]}

    mock_post.side_effect = [
        httpx.TimeoutException("timeout"),
        httpx.TimeoutException("timeout"),
        success_response,
    ]

    async def run_test():
        async with httpx.AsyncClient() as http_client:
            client = AsyncEmbeddingClient(api_key="test-key")
            embedding = await client.embed_single("test text", http_client)
            assert embedding.shape[0] == 3

    asyncio.run(run_test())
    assert mock_post.call_count == 3


def test_error_response_has_required_fields(client):
    resp = client.post("/ask", json={"query": EMPTY_QUERY}, headers={"x-api-key": VALID_API_KEY})
    data = resp.json()
    assert "error" in data
    assert "message" in data


def test_error_code_is_descriptive(client):
    resp = client.post("/ask", json={"query": EMPTY_QUERY}, headers={"x-api-key": VALID_API_KEY})
    assert resp.json()["error"] in ["INVALID_REQUEST", "RATE_LIMIT_EXCEEDED", "REQUEST_TIMEOUT", "API_ERROR"]


def test_rate_limit_enforcement_statuses_are_valid(client):
    responses = []
    for i in range(6):
        resp = client.post("/ask", json={"query": f"test query {i}"}, headers={"x-api-key": VALID_API_KEY})
        responses.append(resp.status_code)
    assert all(code in [200, 400, 429, 503, 504] for code in responses)


def test_multiple_queries_handled(client):
    queries = ["What is AI governance?", "What is data governance?", "What is risk management?"]
    statuses = []
    for query in queries:
        statuses.append(client.post("/ask", json={"query": query}, headers={"x-api-key": VALID_API_KEY}).status_code)
    assert all(s in [200, 429, 503, 504] for s in statuses)


def test_citation_normalization_and_spacing():
    service = RAGService()
    answer = "Policy requires controls [Source:01_Data_Governance_Policy]."
    normalized = service._normalize_answer_citations(answer, ["01_Data_Governance_Policy"])
    assert "(Source: 01_Data_Governance_Policy)" in normalized


def test_citation_appended_when_missing():
    service = RAGService()
    answer = "Policy requires controls across enterprise data."
    normalized = service._normalize_answer_citations(answer, ["01_Data_Governance_Policy"])
    assert normalized.endswith("(Source: 01_Data_Governance_Policy)")


def test_confidence_in_expected_range():
    service = RAGService()
    contexts = [
        {"doc_id": "01_Data_Governance_Policy", "content": "Data governance policy controls.", "relevance_score": 0.7},
        {"doc_id": "05_Information_Security_Policy", "content": "Security controls and monitoring.", "relevance_score": 0.5},
    ]
    answer = "Data governance policy includes controls. (Source: 01_Data_Governance_Policy)"
    confidence = service.calculate_confidence("what is data governance policy", contexts, answer)
    assert 0.0 <= confidence <= 1.0


def test_metrics_endpoint_returns_structured_payload(client):
    resp = client.get("/metrics", headers={"x-api-key": VALID_API_KEY})
    assert resp.status_code == 200
    data = resp.json()
    assert "cache" in data
    assert "retrieval_time_percentiles_ms" in data
    assert "token_usage" in data
    assert "cost_estimates" in data


def test_metrics_retrieval_endpoint(client):
    with patch("api.routes.load_sample_dataset", return_value=[{"query": "test", "relevant_doc_ids": ["01"]}]), patch(
        "api.routes.evaluate_retriever", return_value={"dataset_size": 1, "precision_at_k": 1.0, "recall_at_k": 1.0, "mrr": 1.0, "ndcg_at_k": 1.0, "k": 3}
    ), patch("api.routes.rag_service.ensure_initialized_async", AsyncMock(return_value=None)):
        resp = client.get("/metrics/retrieval", headers={"x-api-key": VALID_API_KEY})
    assert resp.status_code == 200
    assert "precision_at_k" in resp.json()


def test_metrics_token_usage_endpoint(client):
    resp = client.get("/metrics/token_usage", headers={"x-api-key": VALID_API_KEY})
    assert resp.status_code == 200
    data = resp.json()
    assert "token_usage" in data
    assert "cost_estimates" in data


def test_get_current_user_default_admin_for_legacy(monkeypatch):
    monkeypatch.setenv("SERVICE_API_KEY", "legacy-key")
    monkeypatch.delenv("SERVICE_API_KEYS", raising=False)
    monkeypatch.delenv("RBAC_ROLE_MAP", raising=False)
    user = get_current_user("legacy-key")
    assert user["api_key_id"] == "legacy"
    assert user["role"] == "admin"


def test_rbac_doc_filtering_in_service():
    service = RAGService()
    contexts = [
        {"doc_id": "A", "content": "a"},
        {"doc_id": "B", "content": "b"},
    ]
    filtered = service._filter_contexts_by_allowed_docs(contexts, {"A"})
    assert [doc["doc_id"] for doc in filtered] == ["A"]
