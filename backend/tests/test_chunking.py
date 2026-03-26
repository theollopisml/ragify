"""Tests for chunking logic."""

from app.services.chunking import (
    _build_product_text,
    _split_text_with_overlap,
    _strip_html,
    chunk_article,
    chunk_page,
    chunk_product,
    is_page_relevant,
)
from app.services.models import (
    Article,
    Author,
    Blog,
    Chunk,
    Image,
    Page,
    Product,
    PriceRange,
    Price,
    SEO,
    SourceType,
    Variant,
    VariantOption,
)


# ---------------------------------------------------------------------------
# Fixtures — minimal Shopify objects for testing
# ---------------------------------------------------------------------------


def _make_product(**overrides) -> Product:
    defaults = {
        "id": "gid://shopify/Product/1",
        "title": "Terracotta Pot",
        "handle": "terracotta-pot",
        "description": "A beautiful pot for your plants.",
        "descriptionHtml": "<p>A beautiful pot for your plants.</p>",
        "productType": "Pot",
        "vendor": "PlantShop",
        "tags": ["indoor", "terracotta"],
        "seo": SEO(title="Best Terracotta Pot", description="Perfect for indoor plants."),
        "status": "ACTIVE",
        "createdAt": "2026-03-01T00:00:00Z",
        "updatedAt": "2026-03-15T00:00:00Z",
        "priceRangeV2": PriceRange(
            minVariantPrice=Price(amount="19.99", currencyCode="EUR"),
            maxVariantPrice=Price(amount="29.99", currencyCode="EUR"),
        ),
        "variants": [
            Variant(
                id="gid://shopify/ProductVariant/1",
                title="Small",
                price="19.99",
                sku="TC-S",
                availableForSale=True,
                selectedOptions=[VariantOption(name="Size", value="Small")],
            ),
            Variant(
                id="gid://shopify/ProductVariant/2",
                title="Large",
                price="29.99",
                sku="TC-L",
                availableForSale=True,
                selectedOptions=[VariantOption(name="Size", value="Large")],
            ),
        ],
        "metafields": [],
        "images": [
            Image(url="https://cdn.shopify.com/pot.png", altText="A terracotta pot"),
        ],
    }
    defaults.update(overrides)
    return Product(**defaults)


def _make_article(**overrides) -> Article:
    defaults = {
        "id": "gid://shopify/Article/1",
        "title": "How to Water Your Plants",
        "handle": "how-to-water-your-plants",
        "body": "<p>Water your plants regularly.</p><p>Don't overwater them.</p>",
        "summary": "A guide to watering",
        "tags": ["guide"],
        "author": Author(name="Test Author"),
        "blog": Blog(title="Plant Tips", handle="plant-tips"),
        "publishedAt": "2026-03-01T00:00:00Z",
        "createdAt": "2026-03-01T00:00:00Z",
        "updatedAt": "2026-03-15T00:00:00Z",
    }
    defaults.update(overrides)
    return Article(**defaults)


def _make_page(**overrides) -> Page:
    defaults = {
        "id": "gid://shopify/Page/1",
        "title": "FAQ",
        "handle": "faq",
        "body": "<h2>How to order?</h2><p>Just add to cart!</p>",
        "bodySummary": "How to order? Just add to cart!",
        "createdAt": "2026-03-01T00:00:00Z",
        "updatedAt": "2026-03-15T00:00:00Z",
    }
    defaults.update(overrides)
    return Page(**defaults)


# ---------------------------------------------------------------------------
# _strip_html
# ---------------------------------------------------------------------------


class TestStripHtml:

    def test_strips_tags_and_links(self):
        html = '<p>Hello <a href="https://example.com">world</a></p>'
        result = _strip_html(html)
        assert "Hello" in result
        assert "world" in result
        assert "<" not in result
        assert "https://example.com" not in result

    def test_strips_images(self):
        html = '<p>Text</p><img src="https://img.com/pic.png" alt="pic">'
        result = _strip_html(html)
        assert "img.com" not in result
        assert "Text" in result


# ---------------------------------------------------------------------------
# _build_product_text
# ---------------------------------------------------------------------------


class TestBuildProductText:

    def test_full_product(self):
        product = _make_product()
        text = _build_product_text(product)

        assert text.startswith("# Terracotta Pot")
        assert "A beautiful pot for your plants." in text
        assert "**SEO:** Best Terracotta Pot — Perfect for indoor plants." in text
        assert "**Type:** Pot | **Vendor:** PlantShop" in text
        assert "**Tags:** indoor, terracotta" in text
        assert "Size: Small" in text
        assert "Size: Large" in text

    def test_minimal_product_skips_optional_sections(self):
        product = _make_product(
            description="",
            seo=SEO(title=None, description=None),
            tags=[],
            variants=[],
        )
        text = _build_product_text(product)

        assert text.startswith("# Terracotta Pot")
        assert "**SEO:**" not in text
        assert "**Tags:**" not in text
        assert "**Variants:**" not in text
        # Type/Vendor is always present
        assert "**Type:** Pot | **Vendor:** PlantShop" in text


# ---------------------------------------------------------------------------
# _split_text_with_overlap
# ---------------------------------------------------------------------------


class TestSplitTextWithOverlap:

    def test_empty_text(self):
        assert _split_text_with_overlap(text="") == []
        assert _split_text_with_overlap(text="   ") == []

    def test_text_shorter_than_chunk_size(self):
        result = _split_text_with_overlap(text="Short text", chunk_size=100)
        assert result == ["Short text"]

    def test_text_equal_to_chunk_size(self):
        text = "A" * 500
        result = _split_text_with_overlap(text=text, chunk_size=500)
        assert result == [text]

    def test_chunks_have_correct_max_size(self):
        text = "A" * 100
        chunks = _split_text_with_overlap(text=text, chunk_size=30, chunk_overlap=5)
        for chunk in chunks[:-1]:  # Last chunk can be shorter
            assert len(chunk) == 30

    def test_overlap_between_consecutive_chunks(self):
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # 26 chars
        overlap = 3
        chunks = _split_text_with_overlap(text=text, chunk_size=10, chunk_overlap=overlap)

        for i in range(len(chunks) - 1):
            tail = chunks[i][-overlap:]
            head = chunks[i + 1][:overlap]
            assert tail == head, (
                f"Overlap mismatch between chunk {i} and {i+1}: "
                f"tail={tail!r}, head={head!r}"
            )

    def test_all_text_is_covered(self):
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        chunks = _split_text_with_overlap(text=text, chunk_size=10, chunk_overlap=3)
        # Every character of the original text must appear in at least one chunk
        covered = set()
        step = 10 - 3
        for i, chunk in enumerate(chunks):
            start = i * step
            for j, char in enumerate(chunk):
                covered.add(start + j)
        assert covered == set(range(len(text)))

    def test_overlap_greater_than_size_is_clamped(self):
        chunks = _split_text_with_overlap(
            text="ABCDEFGHIJKLMNOP", chunk_size=10, chunk_overlap=15
        )
        # Should not crash, overlap is clamped to chunk_size - 1
        assert len(chunks) > 0


# ---------------------------------------------------------------------------
# chunk_product
# ---------------------------------------------------------------------------


class TestChunkProduct:

    def test_returns_single_chunk(self):
        product = _make_product()
        chunk = chunk_product(product)

        assert isinstance(chunk, Chunk)
        assert "# Terracotta Pot" in chunk.text

    def test_payload_fields(self):
        product = _make_product()
        chunk = chunk_product(product)

        assert chunk.payload.source_type == SourceType.PRODUCT
        assert chunk.payload.shopify_gid == "gid://shopify/Product/1"
        assert chunk.payload.handle == "terracotta-pot"
        assert chunk.payload.image_url == "https://cdn.shopify.com/pot.png"
        assert chunk.payload.image_alt == "A terracotta pot"
        assert chunk.payload.content_hash  # Non-empty hash
        assert chunk.payload.indexed_at  # Non-empty timestamp
        assert chunk.payload.chunk_index is None  # Products don't have chunk_index

    def test_no_image(self):
        product = _make_product(images=[])
        chunk = chunk_product(product)

        assert chunk.payload.image_url is None
        assert chunk.payload.image_alt is None

    def test_content_hash_changes_with_content(self):
        chunk1 = chunk_product(_make_product(description="Version 1"))
        chunk2 = chunk_product(_make_product(description="Version 2"))

        assert chunk1.payload.content_hash != chunk2.payload.content_hash


# ---------------------------------------------------------------------------
# chunk_article
# ---------------------------------------------------------------------------


class TestChunkArticle:

    def test_short_article_single_chunk(self):
        article = _make_article()
        chunks = chunk_article(article)

        assert len(chunks) == 1
        assert "# How to Water Your Plants — Plant Tips" in chunks[0].text

    def test_payload_fields(self):
        article = _make_article()
        chunks = chunk_article(article)

        assert chunks[0].payload.source_type == SourceType.ARTICLE
        assert chunks[0].payload.shopify_gid == "gid://shopify/Article/1"
        assert chunks[0].payload.handle == "how-to-water-your-plants"
        assert chunks[0].payload.chunk_index == 0

    def test_long_article_multiple_chunks(self):
        # Body long enough to produce multiple chunks
        long_body = "<p>" + "Some sentence here. " * 100 + "</p>"
        article = _make_article(body=long_body)
        chunks = chunk_article(article)

        assert len(chunks) > 1
        # All chunks share the same content_hash (hash of full body)
        hashes = {c.payload.content_hash for c in chunks}
        assert len(hashes) == 1
        # chunk_index is incremental
        indices = [c.payload.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_header_repeated_in_every_chunk(self):
        long_body = "<p>" + "Some sentence here. " * 100 + "</p>"
        article = _make_article(body=long_body)
        chunks = chunk_article(article)

        for chunk in chunks:
            assert chunk.text.startswith("# How to Water Your Plants — Plant Tips")


# ---------------------------------------------------------------------------
# chunk_page
# ---------------------------------------------------------------------------


class TestChunkPage:

    def test_short_page_single_chunk(self):
        page = _make_page()
        chunks = chunk_page(page)

        assert len(chunks) == 1
        assert "# FAQ" in chunks[0].text

    def test_payload_fields(self):
        page = _make_page()
        chunks = chunk_page(page)

        assert chunks[0].payload.source_type == SourceType.PAGE
        assert chunks[0].payload.shopify_gid == "gid://shopify/Page/1"
        assert chunks[0].payload.handle == "faq"


# ---------------------------------------------------------------------------
# is_page_relevant
# ---------------------------------------------------------------------------


class TestIsPageRelevant:

    def test_exact_match(self):
        assert is_page_relevant(_make_page(handle="faq")) is True

    def test_substring_match(self):
        assert is_page_relevant(_make_page(handle="faq-livraison")) is True

    def test_no_match(self):
        assert is_page_relevant(_make_page(handle="contact")) is False

    def test_case_insensitive(self):
        assert is_page_relevant(_make_page(handle="FAQ")) is True
