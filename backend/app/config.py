from pathlib import Path

from pydantic_settings import BaseSettings

ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    shopify_store_url: str = ""
    shopify_client_id: str = ""
    shopify_app_secret: str = ""
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    shopify_app_redirect_uri: str = "http://localhost:8000"
    model_config = {"env_file": ENV_FILE}


settings = Settings()
