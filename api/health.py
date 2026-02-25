from fastapi import APIRouter
from api.service import rag_service

router = APIRouter()

@router.get("/health", tags=["Health"])
def health_check():
    health = rag_service.get_health()
    return {
        "status": "ok",
        "rag_initialized": health["rag_initialized"],
        "init_error": health["init_error"]
    }
