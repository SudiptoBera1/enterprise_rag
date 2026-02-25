"""
Pytest configuration and fixtures for test suite.
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, patch

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure deterministic auth config for tests.
os.environ["SERVICE_API_KEY"] = "test-api-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["RAG_PREWARM_ON_STARTUP"] = "0"

from fastapi.testclient import TestClient
from api.routes import app


@pytest.fixture
def client():
    """Provide FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """Valid API key for tests."""
    return "test-api-key"


@pytest.fixture
def valid_query():
    """Valid test query."""
    return "What is AI governance?"


@pytest.fixture
def empty_query():
    """Empty query for validation tests."""
    return ""


@pytest.fixture
def long_query():
    """Query exceeding 500 character limit."""
    return "What " * 200  # 1000 words


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests."""
    # Ensure test data exists
    test_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "raw"
    )
    if not os.path.exists(test_data_dir):
        os.makedirs(test_data_dir)
    
    yield
    
    # Cleanup (optional)
    # Could remove test cache/index here


@pytest.fixture
def mock_openai_response():
    """Mock response from OpenAI API."""
    return {
        "choices": [
            {
                "message": {
                    "content": "This is a test answer about AI governance policies."
                }
            }
        ],
        "usage": {"total_tokens": 150}
    }


@pytest.fixture(autouse=True)
def mock_rag_service():
    """Mock RAG service calls so tests are deterministic and offline."""
    async_mock = AsyncMock(
        return_value={
            "answer": "AI governance is a framework for managing AI risk.",
            "sources": ["07_AI_Governance_Policy"],
            "confidence": 0.82,
            "_telemetry": {
                "retrieval_ms": 20,
                "generation_ms": 120,
                "token_usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 70,
                    "total_tokens": 120,
                    "estimated_cost_usd": 0.0001,
                },
            },
        }
    )
    init_mock = AsyncMock(return_value=None)
    with patch("api.routes.rag_service.ask_async", async_mock), patch("api.routes.rag_service.ensure_initialized_async", init_mock):
        # Inject deterministic document metadata used by RBAC filtering in routes.
        from api.routes import rag_service
        rag_service.documents = [
            {"doc_id": "01_Data_Governance_Policy", "content": "Data governance policy text"},
            {"doc_id": "07_AI_Governance_Policy", "content": "AI governance policy text"},
            {"doc_id": "09_AI_Model_Validation_SOP", "content": "Model validation SOP text"},
        ]
        yield
