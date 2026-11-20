from unittest.mock import MagicMock, patch

from src.rag import answer_hr_question, retrieve_context


def test_weaviate_connection_failure_returns_friendly_message():
    """RAG should handle Weaviate connection failures gracefully."""

    with patch(
        "src.rag.connect_weaviate",
        side_effect=ConnectionError("Weaviate is unavailable"),
    ):
        result = answer_hr_question("How many sick leave days do I get?")

    assert "couldn't connect" in result.lower()
    assert "policy search service" in result.lower()


def test_empty_retrieval_returns_friendly_message():
    """RAG should handle an empty policy search result."""

    with patch("src.rag.retrieve_context", return_value=[]):
        result = answer_hr_question("What is the office dress code?")

    assert "couldn't find relevant information" in result.lower()


def test_retrieval_returns_policy_chunks():
    """Retrieval should return the policy chunks returned by Weaviate."""

    expected_chunks = [
        {
            "source": "leave_policy.md",
            "text": "Employees receive 10 sick leave days per calendar year.",
            "chunk_index": 0,
            "distance": None,
        }
    ]

    mock_collection = MagicMock()
    mock_weaviate_client = MagicMock()

    mock_weaviate_client.collections.get.return_value = mock_collection

    with (
        patch(
            "src.rag.connect_weaviate",
            return_value=mock_weaviate_client,
        ),
        patch(
            "src.rag.search_policies",
            return_value=expected_chunks,
        ) as mock_search,
    ):
        result = retrieve_context("How many sick leave days do I get?")

    assert result == expected_chunks
    mock_search.assert_called_once()
    mock_weaviate_client.close.assert_called_once()


def test_weaviate_client_closes_after_search_failure():
    """The Weaviate client should close even if retrieval fails."""

    mock_weaviate_client = MagicMock()
    mock_weaviate_client.collections.get.return_value = MagicMock()

    with (
        patch(
            "src.rag.connect_weaviate",
            return_value=mock_weaviate_client,
        ),
        patch(
            "src.rag.search_policies",
            side_effect=RuntimeError("Search failed"),
        ),
    ):
        try:
            retrieve_context("How many sick leave days do I get?")
            assert False, "Expected retrieval to raise RuntimeError"
        except RuntimeError as exc:
            assert str(exc) == "Search failed"

    mock_weaviate_client.close.assert_called_once()