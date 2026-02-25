from fastapi import HTTPException, status


def require_role(user: dict, allowed_roles=None):
    allowed_roles = allowed_roles or ["admin", "user"]
    if user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role permissions.",
        )
    return user


def filter_authorized_doc_ids(user: dict, all_doc_ids):
    """
    Admins can access all documents.
    Users can access only explicitly allowed documents.
    """
    role = user.get("role", "user")
    if role == "admin":
        return set(all_doc_ids)

    allowed = set(user.get("allowed_doc_ids", []))
    return set(doc_id for doc_id in all_doc_ids if doc_id in allowed)
