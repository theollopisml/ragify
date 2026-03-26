"""
Shared test fixtures — real API response samples captured from Shopify dev store.
"""

import pytest


@pytest.fixture
def raw_product():
    """A real product response from Shopify GraphQL API (with nested nodes wrappers)."""
    return {
        "id": "gid://shopify/Product/15608887345483",
        "title": "The Inventory Not Tracked Snowboard",
        "handle": "the-inventory-not-tracked-snowboard",
        "description": "A snowboard for testing purposes",
        "descriptionHtml": "<p>A snowboard for <strong>testing</strong> purposes</p>",
        "productType": "snowboard",
        "vendor": "ragify-test-store",
        "tags": ["Accessory", "Sport", "Winter"],
        "seo": {"title": None, "description": None},
        "status": "ACTIVE",
        "createdAt": "2026-03-23T19:40:37Z",
        "updatedAt": "2026-03-24T07:40:46Z",
        "priceRangeV2": {
            "minVariantPrice": {"amount": "949.95", "currencyCode": "EUR"},
            "maxVariantPrice": {"amount": "949.95", "currencyCode": "EUR"},
        },
        "variants": {
            "nodes": [
                {
                    "id": "gid://shopify/ProductVariant/56869318492491",
                    "title": "Default Title",
                    "price": "949.95",
                    "sku": "sku-untracked-1",
                    "availableForSale": True,
                    "selectedOptions": [{"name": "Title", "value": "Default Title"}],
                }
            ]
        },
        "metafields": {"nodes": []},
        "images": {
            "nodes": [
                {
                    "url": "https://cdn.shopify.com/s/files/1/test/snowboard.png",
                    "altText": "A purple snowboard",
                }
            ]
        },
    }


@pytest.fixture
def raw_product_with_seo(raw_product):
    """A product with SEO fields populated."""
    raw_product["seo"] = {
        "title": "Best Snowboard Ever",
        "description": "The ultimate snowboard for winter sports enthusiasts.",
    }
    raw_product["description"] = "A snowboard for testing purposes"
    return raw_product


@pytest.fixture
def raw_page():
    """A real page response from Shopify GraphQL API."""
    return {
        "id": "gid://shopify/Page/710922928459",
        "title": "Contact",
        "handle": "contact",
        "body": "<h2>Contact Us</h2><p>Send us a message!</p>",
        "bodySummary": "Contact Us Send us a message!",
        "createdAt": "2026-03-23T19:40:16Z",
        "updatedAt": "2026-03-23T19:40:16Z",
    }


@pytest.fixture
def raw_article():
    """A synthetic article response (no articles on dev store yet)."""
    return {
        "id": "gid://shopify/Article/123456789",
        "title": "How to Care for Your Plants",
        "handle": "how-to-care-for-your-plants",
        "body": "<p>Water your plants <strong>regularly</strong>.</p><h2>Sunlight</h2><p>Most plants need light.</p>",
        "summary": "A guide to plant care",
        "tags": ["plants", "guide"],
        "author": {"name": "Test Author"},
        "blog": {"title": "Plant Tips", "handle": "plant-tips"},
        "publishedAt": "2026-03-23T20:00:00Z",
        "createdAt": "2026-03-23T19:00:00Z",
        "updatedAt": "2026-03-23T21:00:00Z",
    }
