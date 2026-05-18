import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "company-service"
    SERVICE_VERSION: str = "1.0.0"

    STORAGE_FILE_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "storage",
        "companies.json",
    )

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
