"""Tests for Pydantic models — validates parsing of Shopify GraphQL responses."""

from app.services.models import Article, Page, Product
from app.services.shopify import _flatten_nodes


class TestFlattenNodes:
    """Test the GraphQL {nodes: [...]} unwrapper."""

    def test_flattens_single_level(self):
        data = {"variants": {"nodes": [{"id": "1"}, {"id": "2"}]}}
        result = _flatten_nodes(data)
        assert result == {"variants": [{"id": "1"}, {"id": "2"}]}

    def test_flattens_nested(self):
        data = {
            "variants": {
                "nodes": [{"id": "1", "options": {"nodes": [{"name": "Size"}]}}]
            }
        }
        result = _flatten_nodes(data)
        assert result["variants"][0]["options"] == [{"name": "Size"}]

    def test_preserves_dicts_without_nodes(self):
        data = {"seo": {"title": "Test", "description": "Desc"}}
        result = _flatten_nodes(data)
        assert result == {"seo": {"title": "Test", "description": "Desc"}}

    def test_preserves_scalars(self):
        data = {"title": "Hello", "tags": ["a", "b"], "active": True}
        result = _flatten_nodes(data)
        assert result == data

    def test_empty_nodes(self):
        data = {"metafields": {"nodes": []}}
        result = _flatten_nodes(data)
        assert result == {"metafields": []}


class TestProductModel:
    """Test Product model parsing from real API data."""

    def test_parses_real_product(self, raw_product):
        flat = _flatten_nodes(raw_product)
        product = Product(**flat)

        assert product.id == "gid://shopify/Product/15608887345483"
        assert product.title == "The Inventory Not Tracked Snowboard"
        assert product.handle == "the-inventory-not-tracked-snowboard"
        assert product.productType == "snowboard"
        assert product.vendor == "ragify-test-store"
        assert product.tags == ["Accessory", "Sport", "Winter"]
        assert product.status == "ACTIVE"

    def test_parses_variants(self, raw_product):
        flat = _flatten_nodes(raw_product)
        product = Product(**flat)

        assert len(product.variants) == 1
        variant = product.variants[0]
        assert variant.price == "949.95"
        assert variant.sku == "sku-untracked-1"
        assert variant.availableForSale is True
        assert variant.selectedOptions[0].name == "Title"

    def test_parses_price_range(self, raw_product):
        flat = _flatten_nodes(raw_product)
        product = Product(**flat)

        assert product.priceRangeV2.minVariantPrice.amount == "949.95"
        assert product.priceRangeV2.minVariantPrice.currencyCode == "EUR"

    def test_parses_images(self, raw_product):
        flat = _flatten_nodes(raw_product)
        product = Product(**flat)

        assert len(product.images) == 1
        assert product.images[0].altText == "A purple snowboard"

    def test_handles_null_seo(self, raw_product):
        flat = _flatten_nodes(raw_product)
        product = Product(**flat)

        assert product.seo.title is None
        assert product.seo.description is None

    def test_handles_populated_seo(self, raw_product_with_seo):
        flat = _flatten_nodes(raw_product_with_seo)
        product = Product(**flat)

        assert product.seo.title == "Best Snowboard Ever"
        assert product.seo.description is not None

    def test_handles_empty_metafields(self, raw_product):
        flat = _flatten_nodes(raw_product)
        product = Product(**flat)

        assert product.metafields == []


class TestArticleModel:
    """Test Article model parsing."""

    def test_parses_article(self, raw_article):
        article = Article(**raw_article)

        assert article.id == "gid://shopify/Article/123456789"
        assert article.title == "How to Care for Your Plants"
        assert article.blog.handle == "plant-tips"
        assert article.author is not None and article.author.name == "Test Author"
        assert article.tags == ["plants", "guide"]

    def test_handles_null_summary(self, raw_article):
        raw_article["summary"] = None
        article = Article(**raw_article)

        assert article.summary is None

    def test_handles_null_published_at(self, raw_article):
        raw_article["publishedAt"] = None
        article = Article(**raw_article)

        assert article.publishedAt is None

    def test_handles_null_author(self, raw_article):
        raw_article["author"] = None
        article = Article(**raw_article)

        assert article.author is None

    def test_handles_null_updated_at(self, raw_article):
        raw_article["updatedAt"] = None
        article = Article(**raw_article)

        assert article.updatedAt is None


class TestPageModel:
    """Test Page model parsing."""

    def test_parses_page(self, raw_page):
        page = Page(**raw_page)

        assert page.id == "gid://shopify/Page/710922928459"
        assert page.title == "Contact"
        assert page.handle == "contact"

    def test_body_summary_is_required(self, raw_page):
        page = Page(**raw_page)

        assert page.bodySummary == "Contact Us Send us a message!"
