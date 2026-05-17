import json
import logging
import time

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Simple in-process TTL cache — avoids hitting Secrets Manager on every request.
# The cached value is refreshed after CACHE_TTL_SECONDS (default 5 minutes).
# ---------------------------------------------------------------------------
_cache: dict = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def get_deal_service_url(
    secret_name: str = "lb_endpoint",
    region_name: str = "us-east-1",
    fallback: str = "http://deal-service.local",
) -> str:
    """
    Fetch the Deal Service load-balancer URL from AWS Secrets Manager.

    The secret value is expected to be either:
      - A plain string:  "http://my-alb-endpoint.us-east-1.elb.amazonaws.com"
      - A JSON object:   {"deal_service_url": "http://..."}

    Result is cached in-process for CACHE_TTL_SECONDS to avoid per-request
    Secrets Manager API calls (latency + throttling risk in ECS).

    Falls back to `fallback` when running locally (no AWS credentials / secret not found).
    """
    cache_key = f"{secret_name}:{region_name}"
    cached = _cache.get(cache_key)
    if cached and (time.monotonic() - cached["ts"]) < CACHE_TTL_SECONDS:
        logger.debug("Returning Deal Service URL from cache.")
        return cached["url"]

    url = _fetch_secret(secret_name, region_name, fallback)
    _cache[cache_key] = {"url": url, "ts": time.monotonic()}
    return url


def _fetch_secret(secret_name: str, region_name: str, fallback: str) -> str:
    try:
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=region_name)
        response = client.get_secret_value(SecretId=secret_name)
        secret = response["SecretString"]

        # Accept both {"deal_service_url": "..."} and plain strings.
        try:
            data = json.loads(secret)
            if isinstance(data, dict):
                url = data.get("deal_service_url") or data.get("DEAL_SERVICE_URL") or fallback
            else:
                url = str(data)
        except (json.JSONDecodeError, ValueError):
            url = secret.strip()

        logger.info("Loaded Deal Service URL from AWS Secrets Manager.")
        return url

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.warning(
            f"Could not fetch secret '{secret_name}' from Secrets Manager "
            f"(error: {error_code}). Falling back to default URL."
        )
        return fallback
    except Exception as e:
        logger.warning(
            f"Unexpected error fetching secret '{secret_name}': {e}. "
            "Falling back to default URL."
        )
        return fallback
