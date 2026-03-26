"""Tests for Shopify fetch functions — mocks the GraphQL API layer."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.models import Article, Page, Product
from app.services.shopify import fetch_all_articles, fetch_all_pages, fetch_all_products


@pytest.fixture
def mock_graphql():
    """Patch _graphql_request to avoid real API calls."""
    with patch("app.services.shopify._graphql_request", new_callable=AsyncMock) as mock:
        yield mock


class TestFetchAllProducts:

    @pytest.mark.asyncio
    async def test_returns_typed_products(self, mock_graphql, raw_product):
        mock_graphql.return_value = {
            "products": {
                "nodes": [raw_product],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        products = await fetch_all_products()

        assert len(products) == 1
        assert isinstance(products[0], Product)
        assert products[0].title == "The Inventory Not Tracked Snowboard"

    @pytest.mark.asyncio
    async def test_handles_pagination(self, mock_graphql, raw_product):
        second_product = {**raw_product, "id": "gid://shopify/Product/999", "title": "Second Board"}
        mock_graphql.side_effect = [
            {
                "products": {
                    "nodes": [raw_product],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor1"},
                }
            },
            {
                "products": {
                    "nodes": [second_product],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
        ]

        products = await fetch_all_products()

        assert len(products) == 2
        assert products[1].title == "Second Board"
        assert mock_graphql.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, mock_graphql):
        mock_graphql.return_value = {
            "products": {
                "nodes": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        products = await fetch_all_products()
        assert products == []


class TestFetchAllArticles:

    @pytest.mark.asyncio
    async def test_returns_typed_articles(self, mock_graphql, raw_article):
        mock_graphql.return_value = {
            "articles": {
                "nodes": [raw_article],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        articles = await fetch_all_articles()

        assert len(articles) == 1
        assert isinstance(articles[0], Article)
        assert articles[0].blog.handle == "plant-tips"


class TestFetchAllPages:

    @pytest.mark.asyncio
    async def test_returns_typed_pages(self, mock_graphql, raw_page):
        mock_graphql.return_value = {
            "pages": {
                "nodes": [raw_page],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        pages = await fetch_all_pages()

        assert len(pages) == 1
        assert isinstance(pages[0], Page)
        assert pages[0].handle == "contact"
