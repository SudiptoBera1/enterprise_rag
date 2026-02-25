from typing import Optional


class RAGException(Exception):
    """
    Base exception for all RAG-related errors.
    """

    def __init__(
        self,
        error_code: str,
        message: str,
        details: Optional[str] = None,
        status_code: int = 500
    ):
        self.error_code = error_code
        self.message = message
        self.details = details
        self.status_code = status_code

        super().__init__(message)


class InitializationError(RAGException):
    def __init__(self, details: Optional[str] = None):
        super().__init__(
            error_code="RAG_INITIALIZATION_FAILED",
            message="Failed to initialize RAG system.",
            details=details,
            status_code=500
        )


class ProcessingError(RAGException):
    def __init__(self, details: Optional[str] = None):
        super().__init__(
            error_code="RAG_PROCESSING_FAILED",
            message="Failed to process query.",
            details=details,
            status_code=500
        )


class AuthenticationError(RAGException):
    def __init__(self, details: Optional[str] = None):
        super().__init__(
            error_code="AUTHENTICATION_FAILED",
            message="Authentication failed.",
            details=details,
            status_code=401
        )


class ValidationError(RAGException):
    def __init__(self, details: Optional[str] = None):
        super().__init__(
            error_code="INVALID_REQUEST",
            message="Invalid request.",
            details=details,
            status_code=400
        )


class APIError(RAGException):
    """External API (OpenAI) failure."""
    def __init__(self, details: Optional[str] = None):
        super().__init__(
            error_code="API_ERROR",
            message="External API error (OpenAI unavailable or rate limited).",
            details=details,
            status_code=503
        )


class TimeoutError(RAGException):
    """Request timeout."""
    def __init__(self, details: Optional[str] = None):
        super().__init__(
            error_code="REQUEST_TIMEOUT",
            message="Request timed out. Please try again.",
            details=details,
            status_code=504
        )