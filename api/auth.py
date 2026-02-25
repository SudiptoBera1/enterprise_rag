import os
from fastapi import Header, HTTPException, status


def _load_api_key_map():
    key_map = {}

    raw_multi = os.getenv("SERVICE_API_KEYS", "").strip()
    if raw_multi:
        for item in raw_multi.split(","):
            token = item.strip()
            if not token:
                continue
            if ":" in token:
                key_id, key = token.split(":", 1)
                key_map[key.strip()] = key_id.strip() or "key"
            else:
                key_map[token] = "default"

    legacy = os.getenv("SERVICE_API_KEY")
    if legacy:
        key_map.setdefault(legacy, "legacy")

    return key_map


def _load_role_map():
    raw = os.getenv("RBAC_ROLE_MAP", "legacy:admin,default:user").strip()
    role_map = {}
    if not raw:
        return role_map
    for item in raw.split(","):
        token = item.strip()
        if not token or ":" not in token:
            continue
        key_id, role = token.split(":", 1)
        role_map[key_id.strip()] = role.strip()
    return role_map


def _load_doc_access_map():
    """
    RBAC_DOC_ACCESS_MAP format:
    key_id:doc1|doc2,key_id2:doc3|doc4
    """
    raw = os.getenv("RBAC_DOC_ACCESS_MAP", "").strip()
    access_map = {}
    if not raw:
        return access_map

    for item in raw.split(","):
        token = item.strip()
        if not token or ":" not in token:
            continue
        key_id, docs = token.split(":", 1)
        doc_ids = [d.strip() for d in docs.split("|") if d.strip()]
        access_map[key_id.strip()] = doc_ids

    return access_map


def get_current_user(x_api_key: str = Header(None)):
    key_map = _load_api_key_map()
    if not key_map:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication not configured.",
        )

    if x_api_key not in key_map:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key.",
        )

    api_key_id = key_map[x_api_key]
    role_map = _load_role_map()
    doc_access_map = _load_doc_access_map()

    role = role_map.get(api_key_id, "user")
    allowed_doc_ids = doc_access_map.get(api_key_id, [])

    return {
        "api_key_id": api_key_id,
        "role": role,
        "allowed_doc_ids": allowed_doc_ids,
    }
