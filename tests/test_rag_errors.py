from unittest.mock import MagicMock, patch

from src.rag import answer_hr_question


@patch("src.rag.retrieve_context")
@patch("src.rag.client.responses.create")
def test_quota_exceeded(mock_create, mock_retrieve):
    mock_retrieve.return_value = [
        {
            "source": "leave_policy.md",
            "text": "Employees receive 10 sick leave days.",
        }
    ]
    mock_create.side_effect = Exception(
        "429 RESOURCE_EXHAUSTED: quota exceeded"
    )

    result = answer_hr_question("How many sick leave days do I get?")

    assert "usage limit" in result.lower()
    mock_create.assert_called_once()


@patch("src.rag.retrieve_context")
@patch("src.rag.client.responses.create")
def test_authentication_failure(mock_create, mock_retrieve):
    mock_retrieve.return_value = [
        {
            "source": "leave_policy.md",
            "text": "Employees receive 10 sick leave days.",
        }
    ]
    mock_create.side_effect = Exception("403 PERMISSION_DENIED")

    result = answer_hr_question("How many sick leave days do I get?")

    assert "authorize" in result.lower()
    mock_create.assert_called_once()


@patch("src.rag.retrieve_context")
@patch("src.rag.client.responses.create")
def test_temporary_server_error(mock_create, mock_retrieve):
    mock_retrieve.return_value = [
        {
            "source": "leave_policy.md",
            "text": "Employees receive 10 sick leave days.",
        }
    ]
    mock_create.side_effect = Exception("503 UNAVAILABLE")

    result = answer_hr_question("How many sick leave days do I get?")

    assert "temporarily unavailable" in result.lower()
    assert mock_create.call_count == 3


@patch("src.rag.retrieve_context")
@patch("src.rag.client.responses.create")
def test_empty_model_response(mock_create, mock_retrieve):
    mock_retrieve.return_value = [
        {
            "source": "leave_policy.md",
            "text": "Employees receive 10 sick leave days.",
        }
    ]
    mock_create.return_value = MagicMock(output_text=None)

    result = answer_hr_question("How many sick leave days do I get?")

    assert "empty response" in result.lower()
    mock_create.assert_called_once()