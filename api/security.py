import os
from fastapi import Header, HTTPException, status


def _load_api_key_map():
    """
    Load API keys from env.
    Supported formats:
    - SERVICE_API_KEY=<single-key> (legacy)
    - SERVICE_API_KEYS=id1:key1,id2:key2 or key1,key2
    """
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


def verify_api_key(x_api_key: str = Header(None)):
    key_map = _load_api_key_map()

    if not key_map:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication not configured."
        )

    if x_api_key not in key_map:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key."
        )

    return {"api_key_id": key_map[x_api_key]}
