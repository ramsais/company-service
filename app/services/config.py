import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve environment from process env vars. Default to 'dev'.
_ENV = (os.getenv("ENV") or os.getenv("APP_ENV") or "dev").strip().lower()
_ENV_FILE = ".env.local" if _ENV == "local" else ".env.dev"

# Resolve app directory and env file absolute path (env files now live under app/env/)
_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(_APP_DIR, "env", _ENV_FILE)


class Settings(BaseSettings):
    # Logging & service metadata (must come from env files or process env)
    ENV: str
    LOG_LEVEL: str
    SERVICE_NAME: str
    SERVICE_VERSION: str

    # Secrets / flags (configure via env; no hardcoded defaults)
    INTERNAL_API_KEY: str
    LOCAL_DEVELOPMENT: bool

    # Optional external URL for this service (or upstream dependency)
    COMPANY_SERVICE_URL: str | None = None

    # OpenTelemetry / AWS OTel Collector config
    OTEL_SERVICE_NAME: str | None = None
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None  # e.g. http://localhost:4318 or http://aws-otel-collector:4318
    OTEL_EXPORTER_OTLP_PROTOCOL: str | None = None  # http/protobuf by default when using *_proto_http package
    OTEL_TRACES_SAMPLER: str | None = None  # e.g. always_on, parentbased_traceidratio
    OTEL_TRACES_SAMPLER_ARG: str | None = None
    AWS_XRAY_TRACING_NAME: str | None = None  # optional alias used by AWS X-Ray conventions

    # Integrations & storage (override via env if needed)
    STORAGE_FILE_PATH: str = os.path.join(
        _APP_DIR,
        "storage",
        "companies.json",
    )

    # Pydantic Settings v2 configuration — pick env file based on ENV/APP_ENV
    model_config = SettingsConfigDict(
        env_file=_ENV_PATH,
        env_prefix="",
        case_sensitive=False,
    )


settings = Settings()

