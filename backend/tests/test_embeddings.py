"""Tests for embedding service — mocks the OpenAI API layer."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.embeddings import embed_texts, _MAX_BATCH_SIZE


def _make_embedding_response(embeddings: list[list[float]], start_index: int = 0):
    """Build a fake OpenAI embedding response."""
    response = Mock()
    response.data = [
        Mock(index=start_index + i, embedding=emb)
        for i, emb in enumerate(embeddings)
    ]
    return response


@pytest.fixture
def mock_openai():
    with patch("app.services.embeddings._client") as mock_client:
        mock_client.embeddings = Mock()
        mock_client.embeddings.create = AsyncMock()
        yield mock_client


class TestEmbedTexts:

    @pytest.mark.asyncio
    async def test_empty_list(self, mock_openai):
        result = await embed_texts([])

        assert result == []
        mock_openai.embeddings.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_vectors_in_order(self, mock_openai):
        mock_openai.embeddings.create.return_value = _make_embedding_response(
            [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        )

        result = await embed_texts(["text1", "text2", "text3"])

        assert result == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        mock_openai.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_sorts_by_index_when_unordered(self, mock_openai):
        response = Mock()
        response.data = [
            Mock(index=2, embedding=[0.5, 0.6]),
            Mock(index=0, embedding=[0.1, 0.2]),
            Mock(index=1, embedding=[0.3, 0.4]),
        ]
        mock_openai.embeddings.create.return_value = response

        result = await embed_texts(["a", "b", "c"])

        assert result == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

    @pytest.mark.asyncio
    async def test_batching(self, mock_openai):
        # Create more texts than _MAX_BATCH_SIZE
        num_texts = _MAX_BATCH_SIZE + 10
        texts = [f"text_{i}" for i in range(num_texts)]

        mock_openai.embeddings.create.side_effect = [
            _make_embedding_response([[float(i)] for i in range(_MAX_BATCH_SIZE)]),
            _make_embedding_response([[float(i)] for i in range(10)], start_index=0),
        ]

        result = await embed_texts(texts)

        assert len(result) == num_texts
        assert mock_openai.embeddings.create.call_count == 2
