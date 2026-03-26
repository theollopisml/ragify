"""
Pydantic models for Shopify GraphQL API responses and chunking output.
"""

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
    author: Author
    blog: Blog
    publishedAt: str | None
    createdAt: str
    updatedAt: str


class Page(BaseModel):
    id: str
    title: str
    handle: str
    body: str
    bodySummary: str | None
    createdAt: str
    updatedAt: str


# ---------------------------------------------------------------------------
# Chunking output model
# ---------------------------------------------------------------------------

class Chunk(BaseModel):
    """A single chunk ready for embedding and Qdrant storage."""
    text: str
    payload: dict
