"""
Pydantic models for Shopify GraphQL API responses and chunking output.
"""

from enum import Enum

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Shared models
# ---------------------------------------------------------------------------


class SEO(BaseModel):
    title: str | None
    description: str | None


# ---------------------------------------------------------------------------
# Shopify API response models
# ---------------------------------------------------------------------------


class VariantOption(BaseModel):
    name: str
    value: str


class Variant(BaseModel):
    id: str
    title: str
    price: str
    sku: str | None
    availableForSale: bool
    selectedOptions: list[VariantOption]


class Price(BaseModel):
    amount: str
    currencyCode: str


class PriceRange(BaseModel):
    minVariantPrice: Price
    maxVariantPrice: Price


class Metafield(BaseModel):
    namespace: str
    key: str
    value: str
    type: str


class Image(BaseModel):
    url: str
    altText: str | None


class Product(BaseModel):
    id: str
    title: str
    handle: str
    description: str
    descriptionHtml: str
    productType: str
    vendor: str
    tags: list[str]
    seo: SEO
    status: str
    createdAt: str
    updatedAt: str
    priceRangeV2: PriceRange
    variants: list[Variant]
    metafields: list[Metafield]
    images: list[Image]


class Author(BaseModel):
    name: str


class Blog(BaseModel):
    title: str
    handle: str


class Article(BaseModel):
    id: str
    title: str
    handle: str
    body: str
    summary: str | None
    tags: list[str]
    author: Author | None
    blog: Blog
    publishedAt: str | None
    createdAt: str
    updatedAt: str | None


class Page(BaseModel):
    id: str
    title: str
    handle: str
    body: str
    bodySummary: str
    createdAt: str
    updatedAt: str


# ---------------------------------------------------------------------------
# Chunking output models
# ---------------------------------------------------------------------------


class SourceType(str, Enum):
    PRODUCT = "product"
    ARTICLE = "article"
    PAGE = "page"


class ChunkPayload(BaseModel):
    """Metadata stored alongside the vector in Qdrant."""

    source_type: SourceType
    shopify_gid: str
    handle: str
    content_hash: str
    shopify_updated_at: str | None
    indexed_at: str
    # Product-specific
    image_url: str | None = None
    image_alt: str | None = None
    # Article-specific
    chunk_index: int | None = None


class Chunk(BaseModel):
    """A single chunk ready for embedding and Qdrant storage."""

    text: str
    payload: ChunkPayload
