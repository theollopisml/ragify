"""
Shopify GraphQL Admin API client.

Fetches products, blog articles, and pages (FAQ) from a Shopify store.
All queries use cursor-based pagination (first/after + pageInfo).

API version: 2026-04
Docs: https://shopify.dev/docs/api/admin-graphql/2026-04
"""

import logging

import httpx

from app.config import settings
from app.services.models import Article, Page, Product
from app.services.shopify_auth import shopify_auth

logger = logging.getLogger(__name__)

API_VERSION = "2026-04"
GRAPHQL_URL = (
    f"https://{settings.shopify_store_url}/admin/api/{API_VERSION}/graphql.json"
)

# ---------------------------------------------------------------------------
# GraphQL Queries
# ---------------------------------------------------------------------------

# Products query — fetches all fields needed for RAG indexing
# Fields: title, description (plain + HTML), type, vendor, tags, price range,
#         variants (price, sku), metafields (custom attributes like material, dimensions)
# Source: https://shopify.dev/docs/api/admin-graphql/2026-04/objects/Product
PRODUCTS_QUERY = """
query GetProducts($first: Int!, $after: String) {
    products(first: $first, after: $after) {
        nodes {
            id
            title
            handle
            description
            descriptionHtml
            productType
            vendor
            tags
            seo {
                title
                description
            }
            status
            createdAt
            updatedAt
            priceRangeV2 {
                minVariantPrice { amount currencyCode }
                maxVariantPrice { amount currencyCode }
            }
            #WARNING: Limited to 50 variants — if a product has more, they will be truncated
            variants(first: 50) {
                nodes {
                    id
                    title
                    price
                    sku
                    availableForSale
                    selectedOptions { name value }
                }
            }
            #WARNING: Limited to 20 metafields — if a product has more, they will be truncated
            metafields(first: 20) {
                nodes {
                    namespace
                    key
                    value
                    type
                }
            }
            images(first: 5) {
                nodes {
                    url
                    altText
                }
            }
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""

# Blog articles query — fetches content for RAG (guides, tips, etc.)
# Fields: title, body (HTML), summary, tags, author, blog name
# Source: https://shopify.dev/docs/api/admin-graphql/2026-04/objects/Article
ARTICLES_QUERY = """
query GetArticles($first: Int!, $after: String) {
    articles(first: $first, after: $after) {
        nodes {
            id
            title
            handle
            body
            summary
            tags
            author {
                name
            }
            blog {
                title
                handle
            }
            publishedAt
            createdAt
            updatedAt
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""

# Pages query — fetches FAQ and static content pages
# Fields: title, body (HTML), handle
# Source: https://shopify.dev/docs/api/admin-graphql/2026-04/objects/Page
PAGES_QUERY = """
query GetPages($first: Int!, $after: String) {
    pages(first: $first, after: $after) {
        nodes {
            id
            title
            handle
            body
            bodySummary
            createdAt
            updatedAt
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------


async def _graphql_request(query: str, variables: dict) -> dict:
    """Send a GraphQL request to Shopify Admin API."""
    token = await shopify_auth.get_access_token()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url=GRAPHQL_URL,
            headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
            },
            json={"query": query, "variables": variables},
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            raise ValueError(f"GraphQL errors: {data['errors']}")

        return data["data"]


async def _fetch_all(query: str, resource_key: str, batch_size: int = 50) -> list[dict]:
    """Fetch all items of a resource using cursor-based pagination.

    Args:
        query: The GraphQL query string (must accept $first and $after variables)
        resource_key: The top-level key in the response (e.g. "products", "articles")
        batch_size: Number of items per page (max 250, default 50)
    """
    all_items = []
    cursor = None

    while True:
        data = await _graphql_request(query, {"first": batch_size, "after": cursor})
        resource = data[resource_key]
        all_items.extend(resource["nodes"])

        page_info = resource["pageInfo"]
        if not page_info["hasNextPage"]:
            break

        cursor = page_info["endCursor"]
        logger.info(f"Fetched {len(all_items)} {resource_key} so far...")

    logger.info(f"Fetched {len(all_items)} {resource_key} total.")
    return all_items


def _flatten_nodes(item: dict) -> dict:
    """Flatten nested {nodes: [...]} wrappers from GraphQL responses into plain lists."""
    flattened = {}
    for key, value in item.items():
        if isinstance(value, dict) and "nodes" in value and len(value) == 1:
            flattened[key] = [_flatten_nodes(node) for node in value["nodes"]]
        elif isinstance(value, dict):
            flattened[key] = _flatten_nodes(value)
        else:
            flattened[key] = value
    return flattened


async def fetch_all_products() -> list[Product]:
    """Fetch all products from the Shopify store."""
    raw = await _fetch_all(PRODUCTS_QUERY, "products")
    return [Product(**_flatten_nodes(item)) for item in raw]


async def fetch_all_articles() -> list[Article]:
    """Fetch all blog articles from the Shopify store."""
    raw = await _fetch_all(ARTICLES_QUERY, "articles")
    return [Article(**item) for item in raw]


async def fetch_all_pages() -> list[Page]:
    """Fetch all pages (FAQ, static content) from the Shopify store."""
    raw = await _fetch_all(PAGES_QUERY, "pages")
    return [Page(**item) for item in raw]
