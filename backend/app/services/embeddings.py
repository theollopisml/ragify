"""
Embedding service — transforms text into vectors via OpenAI API.

Uses text-embedding-3-small (1536 dimensions) by default.
Handles batching to stay within API limits (max 2048 texts per request).
"""

import logging

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# OpenAI client — initialized once, reused across calls
_client = AsyncOpenAI(api_key=settings.openai_api_key)

# OpenAI embedding API accepts max 2048 texts per request
_MAX_BATCH_SIZE = 2048


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Convert a list of texts into embedding vectors.

    Args:
        texts: List of strings to embed.

    Returns:
        List of vectors (list of floats), one per input text, in the same order.
    """
    if not texts:
        return []

    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), _MAX_BATCH_SIZE):
        batch = texts[i : i + _MAX_BATCH_SIZE]
        logger.info("Embedding batch %d–%d of %d texts", i, i + len(batch), len(texts))

        response = await _client.embeddings.create(
            input=batch,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )

        # Response data is sorted by index, but we sort explicitly to be safe
        batch_embeddings = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings
