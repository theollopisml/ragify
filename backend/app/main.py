import logging

from fastapi import FastAPI

from app.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ragify",
    description="Assistant IA RAG pour boutique Shopify",
)


@app.on_event("startup")
async def on_startup():
    logger.info("Ragify backend started")


@app.get("/health")
async def health():
    """Endpoint de santé — vérifie que le backend tourne."""
    return {"status": "ok"}
