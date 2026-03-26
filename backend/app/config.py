from pathlib import Path

from pydantic_settings import BaseSettings

# Resolve .env from project root (backend/app/config.py → ragify/.env)
# In Docker the file doesn't exist — Pydantic ignores it and reads system env vars
ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    shopify_store_url: str = ""
    shopify_client_id: str = ""
    shopify_app_secret: str = ""
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    # Chunking — comma-separated list of page handles to index (e.g. "faq,about")
    pages_handles_to_index: str = "faq"
    chunk_size: int = 500
    chunk_overlap: int = 50
    model_config = {"env_file": ENV_FILE}


settings = Settings()
