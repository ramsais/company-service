import httpx
import logging
import socket
from app.schemas.company import Deal
from app.services.config import settings
from app.middleware import _correlation_ctx, CORRELATION_ID_HEADER

logger = logging.getLogger(__name__)

class DealServiceClient:
    def __init__(self, base_url: str | None = None):
        # Resolve lazily so the URL is fetched from config at request time
        self.base_url = (base_url or settings.DEAL_SERVICE_URL).rstrip("/")
        logger.info(f"DealServiceClient initialized with base_url: {self.base_url}")
        # Extract hostname for diagnostics
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.base_url)
            self.hostname = parsed.hostname
            logger.info(f"Parsed hostname from URL: {self.hostname}")
        except Exception as e:
            logger.error(f"Failed to parse URL: {e}")
            self.hostname = None

    async def _verify_dns_resolution(self) -> bool:
        """Try to resolve the hostname to help diagnose connection issues."""
        if not self.hostname:
            logger.warning(f"Cannot verify DNS: hostname is None")
            return False

        try:
            logger.info(f"Attempting to resolve hostname: {self.hostname}")
            ip = socket.gethostbyname(self.hostname)
            logger.info(f"DNS resolution successful: {self.hostname} -> {ip}")
            return True
        except socket.gaierror as e:
            logger.error(f"DNS resolution FAILED for {self.hostname}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during DNS resolution: {e}")
            return False

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
                    logger.warning(f"Deal API returned non-200 status_code={response.status_code} for company_id={company_id}, response_body={response.text[:500]}")
                    return []
        except httpx.TimeoutException as e:
            logger.error(f"TIMEOUT (5s) connecting to Deal API at {url} for company_id={company_id}: {e}")
            # Try DNS resolution diagnostic
            await self._verify_dns_resolution()
            return []
        except httpx.ConnectError as e:
            logger.error(f"CONNECTION ERROR to Deal API at {url} for company_id={company_id}: {e}")
            # Try DNS resolution diagnostic
            await self._verify_dns_resolution()
            logger.error(f"Please verify: 1) Deal service is running, 2) URL is correct, 3) Security groups allow traffic on port {self._extract_port()}, 4) Deal service DNS ({self.hostname}) resolves correctly")
            return []
        except httpx.RequestError as e:
            logger.error(f"REQUEST ERROR connecting to Deal API at {url} for company_id={company_id}: {e}")
            # Try DNS resolution diagnostic
            await self._verify_dns_resolution()
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching deals from {url} for company_id={company_id}: {type(e).__name__}: {e}", exc_info=True)
            return []

    def _extract_port(self) -> str:
        """Extract port from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.base_url)
            return str(parsed.port or 80)
        except:
            return "unknown"




