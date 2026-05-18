import json
import base64
import logging
from fastapi import Header, HTTPException, Request
from typing import Optional

from app.services.config import settings

logger = logging.getLogger(__name__)


def _decode_jwt_payload(token: str) -> dict:
    """Decode the payload from a JWT token without verification (API Gateway already validated it)."""
    logger.debug(f"Decoding JWT token")
    try:
        parts = token.split(".")
        if len(parts) != 3:
            logger.warning(f"Invalid JWT format: expected 3 parts, got {len(parts)}")
            raise ValueError("Invalid JWT format")
        payload = parts[1]
        # Add padding if needed
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded)
        logger.debug(f"Successfully decoded JWT, claims keys: {list(claims.keys())}")
        return claims
    except Exception as e:
        logger.error(f"Error decoding JWT token: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid or malformed authorization token")


def get_current_user_role(request: Request, authorization: Optional[str] = Header(default=None)) -> str:
    """
    Extract the user role from the JWT token passed in the Authorization header.
    API Gateway has already validated the Cognito token; we only decode the payload
    to read the 'cognito:groups' claim and determine the role.

    If the x-internal-api-key header matches the configured key, skip Cognito auth
    and return 'WRITE_USER' (trusted internal caller).

    Returns 'WRITE_USER' or 'READ_USER'.
    """
    internal_key = request.headers.get("x-internal-api-key")
    if internal_key and internal_key == settings.INTERNAL_API_KEY:
        logger.info("Internal API key matched — skipping Cognito auth, granting WRITE_USER")
        return "WRITE_USER"

    logger.info(f"get_current_user_role() called, authorization header present: {authorization is not None}")

    if not authorization:
        logger.warning(f"Authorization header is missing")
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        logger.warning(f"Bearer token is missing or empty after removing prefix")
        raise HTTPException(status_code=401, detail="Bearer token is missing")
    
    logger.debug(f"Bearer token extracted, length={len(token)}")

    claims = _decode_jwt_payload(token)

    groups: list = claims.get("cognito:groups") or []
    logger.info(f"User groups from JWT: {groups}")
    
    if "WRITE_USER" in groups:
        logger.info(f"User role determined: WRITE_USER")
        return "WRITE_USER"
    if "READ_USER" in groups:
        logger.info(f"User role determined: READ_USER")
        return "READ_USER"

    logger.error(f"User does not belong to a recognized role group, available groups: {groups}")
    raise HTTPException(status_code=403, detail="User does not belong to a recognized role group (WRITE_USER or READ_USER)")


def require_write_user(role: str = Header(default=None)) -> str:
    """Dependency that enforces WRITE_USER-only access."""
    logger.info(f"require_write_user() called, role={role}")
    # This is used as a secondary check after get_current_user_role
    if role != "WRITE_USER":
        logger.warning(f"WRITE_USER role required but got role={role}")
        raise HTTPException(status_code=403, detail="WRITE_USER role required for this operation")
    logger.info(f"WRITE_USER role authorized")
    return role
