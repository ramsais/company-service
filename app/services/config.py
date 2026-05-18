import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Hardcoded Deal Service URL
    DEAL_SERVICE_URL: str = "http://deal.dev.svc.local:9000"

    STORAGE_FILE_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "storage",
        "companies.json",
    )

    model_config = SettingsConfigDict(env_file=".env")



settings = Settings()
