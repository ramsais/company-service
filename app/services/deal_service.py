import httpx
import logging
from app.schemas.company import Deal
from app.services.config import settings
from app.middleware import _correlation_ctx, CORRELATION_ID_HEADER

logger = logging.getLogger(__name__)

class DealServiceClient:
    def __init__(self, base_url: str | None = None):
        # Resolve lazily so the URL is fetched from config at request time
        self.base_url = (base_url or settings.DEAL_SERVICE_URL).rstrip("/")
        logger.info(f"DealServiceClient initialized with base_url: {self.base_url}")

    async def get_deals_for_company(self, company_id: str) -> list[Deal]:
        url = f"{self.base_url}/deals"
        params = {"company_id": company_id}
        correlation_id = _correlation_ctx.get("-")

        logger.info(f"Fetching deals for company_id={company_id}, url={url}, correlation_id={correlation_id}")

        headers = {CORRELATION_ID_HEADER: correlation_id}
        try:
            logger.debug(f"Creating AsyncClient with timeout=5.0 for {url}")
            async with httpx.AsyncClient(timeout=5.0) as client:
                logger.debug(f"Sending GET request to {url} with params {params}")
                response = await client.get(url, params=params, headers=headers)
                logger.info(f"Received response status_code={response.status_code} for company_id={company_id}")

                if response.status_code == 200:
                    deals_data = response.json()
                    logger.info(f"Successfully parsed {len(deals_data)} deals for company_id={company_id}")
                    deals = [Deal(**d) for d in deals_data]
                    logger.debug(f"Converted deals to Deal objects: {[d.id for d in deals]}")
                    return deals
                else:
                    logger.warning(f"Deal API returned non-200 status_code={response.status_code} for company_id={company_id}, response_body={response.text}")
                    return []
        except httpx.TimeoutException as e:
            logger.error(f"Timeout connecting to Deal API at {url} for company_id={company_id}: {e}", exc_info=True)
            return []
        except httpx.RequestError as e:
            logger.error(f"RequestError connecting to Deal API at {url} for company_id={company_id}: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching deals from {url} for company_id={company_id}: {e}", exc_info=True)
            return []


