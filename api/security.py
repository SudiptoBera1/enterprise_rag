from api.auth import get_current_user
from fastapi import Header


def verify_api_key(x_api_key: str = Header(None)):
    # Backward-compatible wrapper used by existing code paths.
    # Prefer using api.auth.get_current_user directly for RBAC-aware auth.
    return get_current_user(x_api_key)
