import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.logging import setup_logging
from app.services.shopify_auth import shopify_auth

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — runs on startup and shutdown."""
    logger.info("Starting application...")
    try:
        await shopify_auth.get_access_token()
        logger.info("Shopify token retrieved successfully on startup.")
    except Exception as e:
        logger.error(f"Failed to retrieve Shopify token on startup: {e}")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="Ragify",
    description="RAG-powered AI assistant for Shopify stores",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
