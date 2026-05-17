import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.services.secrets import get_deal_service_url


class Settings(BaseSettings):
    # AWS Secrets Manager config — override via env vars if needed
    AWS_SECRET_NAME: str = "lb_endpoint"
    AWS_REGION: str = "us-east-1"

    # Fallback used locally when Secrets Manager is unreachable
    DEAL_SERVICE_URL_FALLBACK: str = "http://deal-service.local"

    STORAGE_FILE_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "storage",
        "companies.json",
    )

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def DEAL_SERVICE_URL(self) -> str:
        return get_deal_service_url(
            secret_name=self.AWS_SECRET_NAME,
            region_name=self.AWS_REGION,
            fallback=self.DEAL_SERVICE_URL_FALLBACK,
        )


settings = Settings()
