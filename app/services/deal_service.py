import httpx
import logging
from app.schemas.company import Deal
from app.services.config import settings
from app.middleware import _correlation_ctx, CORRELATION_ID_HEADER

logger = logging.getLogger(__name__)

class DealServiceClient:
    def __init__(self, base_url: str | None = None):
        # Resolve lazily so the URL is fetched from Secrets Manager at request time,
        # not at import time. Allows tests to override settings before instantiation.
        self.base_url = (base_url or settings.DEAL_SERVICE_URL).rstrip("/")

    async def get_deals_for_company(self, company_id: str) -> list[Deal]:
        url = f"{self.base_url}/deals"
        params = {"company_id": company_id}
        
        headers = {CORRELATION_ID_HEADER: _correlation_ctx.get("-")}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, params=params, headers=headers)
                if response.status_code == 200:
                    deals_data = response.json()
                    return [Deal(**d) for d in deals_data]
                else:
                    logger.warning(f"Deal API returned status {response.status_code} for company {company_id}")
                    return []
        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.error(f"Error connecting to Deal API: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching deals: {e}")
            return []
