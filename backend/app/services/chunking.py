"""
Chunking logic — transforms Shopify data into Chunk objects ready for embedding.

Each function takes a single Shopify object and returns one or more Chunks.
The text field is what gets embedded, the payload is metadata stored in Qdrant.
"""

import hashlib
import logging
from datetime import datetime, timezone
from unicodedata import normalize

import html2text

from app.config import settings
from app.services.models import (
    Article,
    Chunk,
    ChunkPayload,
    Page,
    Product,
    SourceType,
)

logger = logging.getLogger(__name__)

# html2text converter — configured once, reused across calls
_html_converter = html2text.HTML2Text()
_html_converter.ignore_links = True
_html_converter.ignore_images = True
_html_converter.body_width = 0  # No line wrapping


def _content_hash(text: str) -> str:
    """SHA-256 hash of the text content, used for change detection during sync."""
    return hashlib.sha256(text.encode()).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_html(html: str) -> str:
    """Convert HTML to clean plain text (markdown-ish)."""
    return _html_converter.handle(html).strip()


# ---------------------------------------------------------------------------
# Text builders — construct the markdown text for each content type
# ---------------------------------------------------------------------------


def _build_product_text(product: Product) -> str:
    parts = [f"# {product.title}"]

    if product.description:
        parts.append(product.description)

    if product.seo.title or product.seo.description:
        seo_parts = [s for s in [product.seo.title, product.seo.description] if s]
        parts.append(f"**SEO:** {' — '.join(seo_parts)}")

    parts.append(f"**Type:** {product.productType} | **Vendor:** {product.vendor}")

    if product.tags:
        parts.append(f"**Tags:** {', '.join(product.tags)}")

    if product.variants:
        variant_strs = []
        for v in product.variants:
            options = ", ".join(f"{o.name}: {o.value}" for o in v.selectedOptions)
            variant_strs.append(options)
        parts.append(f"**Variants:** {' / '.join(variant_strs)}")

    return "\n\n".join(parts)


def _build_chunk_text(header: str, chunk_body: str) -> str:
    """Generic builder for chunk text with a header and body."""
    return f"# {header}\n\n{chunk_body}"


# ---------------------------------------------------------------------------
# Product chunking (1 product = 1 chunk)
# ---------------------------------------------------------------------------


def chunk_product(product: Product) -> Chunk:
    """Convert a Shopify Product into a single Chunk."""
    text = _build_product_text(product)

    first_image = product.images[0] if product.images else None

    payload = ChunkPayload(
        source_type=SourceType.PRODUCT,
        shopify_gid=product.id,
        handle=product.handle,
        content_hash=_content_hash(text),
        shopify_updated_at=product.updatedAt,
        indexed_at=_now_iso(),
        image_url=first_image.url if first_image else None,
        image_alt=first_image.altText if first_image else None,
    )

    return Chunk(text=text, payload=payload)


def _chunk_html_content(
    source_type: SourceType,
    gid: str,
    handle: str,
    html_body: str,
    updated_at: str | None,
    header: str,
) -> list[Chunk]:
    """Shared logic for chunking HTML content (articles and pages)."""
    plain_text = _strip_html(html_body)
    text_chunks = _split_text_with_overlap(text=plain_text)

    full_body_hash = _content_hash(html_body)

    chunks: list[Chunk] = []
    for i, chunk_body in enumerate(text_chunks):
        text = _build_chunk_text(header, chunk_body)
        payload = ChunkPayload(
            source_type=source_type,
            shopify_gid=gid,
            handle=handle,
            content_hash=full_body_hash,
            shopify_updated_at=updated_at,
            indexed_at=_now_iso(),
            chunk_index=i,
        )
        chunks.append(Chunk(text=text, payload=payload))

    return chunks


# ---------------------------------------------------------------------------
# Article chunking (1 article = N chunks with overlap)
# ---------------------------------------------------------------------------


def chunk_article(article: Article) -> list[Chunk]:
    """Convert a Shopify Article into one or more Chunks."""
    return _chunk_html_content(
        source_type=SourceType.ARTICLE,
        gid=article.id,
        handle=article.handle,
        html_body=article.body,
        updated_at=article.updatedAt,
        header=f"{article.title} — {article.blog.title}",
    )


# ---------------------------------------------------------------------------
# Page chunking (same split logic as articles)
# ---------------------------------------------------------------------------


def chunk_page(page: Page) -> list[Chunk]:
    """Convert a Shopify Page into one or more Chunks."""
    return _chunk_html_content(
        source_type=SourceType.PAGE,
        gid=page.id,
        handle=page.handle,
        html_body=page.body,
        updated_at=page.updatedAt,
        header=page.title,
    )


# ---------------------------------------------------------------------------
# Page filtering — only index relevant pages
# ---------------------------------------------------------------------------

# Normalized list of handles to index, loaded once from config
_HANDLES_TO_INDEX: set[str] = {
    normalize("NFC", h.strip().lower())
    for h in settings.pages_handles_to_index.split(",")
    if h.strip()
}


def is_page_relevant(page: Page) -> bool:
    """Check if a page should be indexed based on its handle (substring match)."""
    normalized_handle = normalize("NFC", page.handle.strip().lower())
    return any(keyword in normalized_handle for keyword in _HANDLES_TO_INDEX)


# ---------------------------------------------------------------------------
# Text splitting with overlap (shared by articles and pages)
# ---------------------------------------------------------------------------


def _split_text_with_overlap(
    *,
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[str]:
    """Split text into chunks by characters, respecting size and overlap.

    Strategy: split into characters, accumulate until chunk_size is reached,
    then start a new chunk with the last characters from the previous chunk
    (enough to cover chunk_overlap characters).
    """
    if not text.strip():
        logger.warning("Text is empty after stripping whitespace. Returning no chunks.")
        return []

    if len(text) <= chunk_size:
        return [text]

    if chunk_overlap >= chunk_size:
        logger.warning(
            "Chunk overlap (%d) is greater than or equal to chunk size (%d). "
            "This may lead to duplicate chunks. Adjusting chunk overlap to %d.",
            chunk_overlap,
            chunk_size,
            chunk_size - 1,
        )
        chunk_overlap = chunk_size - 1

    step = chunk_size - chunk_overlap
    chunks: list[str] = []

    for start in range(0, len(text), step):
        chunks.append(text[start : start + chunk_size])

    return chunks
