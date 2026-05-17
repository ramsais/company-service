import json
import base64
from fastapi import Header, HTTPException
from typing import Optional


def _decode_jwt_payload(token: str) -> dict:
    """Decode the payload from a JWT token without verification (API Gateway already validated it)."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        payload = parts[1]
        # Add padding if needed
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or malformed authorization token")


def get_current_user_role(authorization: Optional[str] = Header(default=None)) -> str:
    """
    Extract the user role from the JWT token passed in the Authorization header.
    API Gateway has already validated the Cognito token; we only decode the payload
    to read the 'cognito:groups' claim and determine the role.

    Returns 'admin' or 'user'.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Bearer token is missing")

    claims = _decode_jwt_payload(token)

    groups: list = claims.get("cognito:groups") or []
    if "admin" in groups:
        return "admin"
    if "user" in groups:
        return "user"

    raise HTTPException(status_code=403, detail="User does not belong to a recognized role group (admin or user)")


def require_admin(role: str = Header(default=None)) -> str:
    """Dependency that enforces admin-only access."""
    # This is used as a secondary check after get_current_user_role
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required for this operation")
    return role
