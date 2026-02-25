from collections import defaultdict
from contextlib import asynccontextmanager
import logging
import os
import time

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import APIConnectionError, APIError as OpenAIAPIError, APITimeoutError, RateLimitError
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.exceptions import APIError, ProcessingError, RAGException, TimeoutError as RAGTimeoutError, ValidationError
from api.health import router as health_router
from api.logging_config import setup_logging
from api.schemas import QueryRequest, QueryResponse
from api.security import verify_api_key
from api.service import rag_service
from llm.async_client import EmbeddingAPIError, EmbeddingRateLimitError, EmbeddingTimeoutError


setup_logging()
logger = logging.getLogger("rag_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Prebuild RAG indices on startup for predictable first-request latency.
    Can be disabled with RAG_PREWARM_ON_STARTUP=0 (used in tests).
    """
    if os.getenv("RAG_PREWARM_ON_STARTUP", "1") != "1":
        logger.info("rag_prewarm_skipped")
    else:
        try:
            await rag_service.ensure_initialized_async()
            logger.info("rag_prewarm_complete")
        except Exception as e:
            logger.error("rag_prewarm_failed", extra={"error_details": str(e)})
    yield


app = FastAPI(title="Enterprise Hybrid RAG API", lifespan=lifespan)


def _parse_origins():
    raw = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "x-api-key"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

app.include_router(health_router)


METRICS = {
    "startup_time": int(time.time()),
    "requests_total": 0,
    "requests_success_total": 0,
    "requests_error_total": 0,
    "error_by_type": defaultdict(int),
    "latency_ms_total": 0,
    "latency_ms_avg": 0.0,
}


@app.exception_handler(RAGException)
async def rag_exception_handler(request: Request, exc: RAGException):
    logger.error(
        "rag_exception",
        extra={
            "error_code": exc.error_code,
            "error_message": exc.message,
            "error_details": exc.details,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc):
    METRICS["requests_error_total"] += 1
    METRICS["error_by_type"]["rate_limit"] += 1
    logger.warning("rate_limit_exceeded", extra={"client_ip": request.client.host})

    return JSONResponse(
        status_code=429,
        content={
            "error": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests. Please try again later.",
        },
    )


@app.post("/ask", response_model=QueryResponse)
@limiter.limit("5/minute")
async def ask_question(request: Request, payload: QueryRequest, auth_ctx: dict = Depends(verify_api_key)):
    METRICS["requests_total"] += 1
    start_time = time.time()
    api_key_id = auth_ctx.get("api_key_id", "unknown")

    if not payload.query or not payload.query.strip():
        logger.warning("empty_query_received", extra={"client_ip": request.client.host if request.client else None, "api_key_id": api_key_id})
        raise ValidationError(details="Query cannot be empty")

    if len(payload.query) > 500:
        logger.warning("query_too_long", extra={"query_length": len(payload.query), "api_key_id": api_key_id})
        raise ValidationError(details="Query too long (max 500 characters)")

    logger.info(
        "query_received",
        extra={
            "query": payload.query,
            "client_ip": request.client.host if request.client else None,
            "api_key_id": api_key_id,
        },
    )

    try:
        result = await rag_service.ask_async(payload.query)
        latency_ms = int((time.time() - start_time) * 1000)
        result["latency_ms"] = latency_ms

        METRICS["requests_success_total"] += 1
        METRICS["latency_ms_total"] += latency_ms
        if METRICS["requests_success_total"] > 0:
            METRICS["latency_ms_avg"] = round(METRICS["latency_ms_total"] / METRICS["requests_success_total"], 2)

        logger.info(
            "query_processed",
            extra={
                "query": payload.query,
                "sources": result["sources"],
                "confidence": result["confidence"],
                "latency_ms": latency_ms,
                "api_key_id": api_key_id,
            },
        )
        return result

    except (EmbeddingRateLimitError, RateLimitError) as e:
        METRICS["requests_error_total"] += 1
        METRICS["error_by_type"]["api_rate_limited"] += 1
        logger.error("api_rate_limited", extra={"query": payload.query, "error_details": str(e), "api_key_id": api_key_id})
        raise APIError(details="OpenAI API rate limited. Please try again shortly.")

    except (EmbeddingTimeoutError, APITimeoutError, APIConnectionError) as e:
        METRICS["requests_error_total"] += 1
        METRICS["error_by_type"]["api_timeout"] += 1
        logger.error("api_timeout", extra={"query": payload.query, "error_details": str(e), "api_key_id": api_key_id})
        raise RAGTimeoutError(details="API request timed out. Please try again.")

    except (EmbeddingAPIError, OpenAIAPIError) as e:
        METRICS["requests_error_total"] += 1
        METRICS["error_by_type"]["api_error"] += 1
        logger.error("api_error", extra={"query": payload.query, "error_details": str(e), "api_key_id": api_key_id})
        raise APIError(details="OpenAI API failed to process the request.")

    except RuntimeError as e:
        METRICS["requests_error_total"] += 1
        METRICS["error_by_type"]["runtime_error"] += 1
        logger.error("runtime_error", extra={"query": payload.query, "error_details": str(e), "api_key_id": api_key_id})
        raise ProcessingError(details=f"Failed to process query: {str(e)}")

    except RAGException:
        raise

    except Exception as e:
        METRICS["requests_error_total"] += 1
        METRICS["error_by_type"]["unexpected_error"] += 1
        logger.error(
            "unexpected_error",
            extra={
                "query": payload.query,
                "error_details": str(e),
                "error_type": type(e).__name__,
                "api_key_id": api_key_id,
            },
        )
        raise ProcessingError(details="An unexpected error occurred. Please try again later.")


@app.get("/metrics", dependencies=[Depends(verify_api_key)], tags=["Monitoring"])
async def metrics():
    return {
        "startup_time": METRICS["startup_time"],
        "requests_total": METRICS["requests_total"],
        "requests_success_total": METRICS["requests_success_total"],
        "requests_error_total": METRICS["requests_error_total"],
        "error_by_type": dict(METRICS["error_by_type"]),
        "latency_ms_avg": METRICS["latency_ms_avg"],
    }
