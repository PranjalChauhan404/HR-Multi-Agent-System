from unittest.mock import MagicMock, patch

from src.router import format_conversation_history, route_request


def test_empty_history():
    assert format_conversation_history(None) == "No previous conversation."
    assert format_conversation_history([]) == "No previous conversation."


def test_format_message_history():
    history = [
        {
            "role": "user",
            "content": "How many sick leave days do I get?",
        },
        {
            "role": "assistant",
            "content": "You receive 10 sick leave days.",
        },
    ]

    result = format_conversation_history(history)

    assert "User: How many sick leave days do I get?" in result
    assert "Assistant: You receive 10 sick leave days." in result


def test_history_limited_to_recent_messages():
    history = [
        {"role": "user", "content": f"Message {i}"}
        for i in range(10)
    ]

    result = format_conversation_history(
        history,
        max_messages=3,
    )

    assert "Message 7" in result
    assert "Message 8" in result
    assert "Message 9" in result
    assert "Message 0" not in result


@patch("src.router.Crew")
def test_router_passes_history_to_task(mock_crew_class):
    mock_crew = MagicMock()
    mock_crew.kickoff.return_value = "Mocked HR response"
    mock_crew_class.return_value = mock_crew

    history = [
        {
            "role": "user",
            "content": "How many sick leave days do I get?",
        },
        {
            "role": "assistant",
            "content": "You receive 10 sick leave days.",
        },
    ]

    result = route_request(
        user_message="What about casual leave?",
        employee_id=4,
        history=history,
    )

    assert result == "Mocked HR response"
    mock_crew_class.assert_called_once()
    mock_crew.kickoff.assert_called_once()


@patch("src.router.answer_hr_question")
@patch("src.router.Crew")
def test_router_handles_request_without_history(
    mock_crew_class,
    mock_answer_hr_question,
):
    expected_answer = (
        "Employees receive 10 sick leave days per calendar year."
    )
    mock_answer_hr_question.return_value = expected_answer

    result = route_request(
        user_message="How many sick leave days do employees receive?",
        employee_id=4,
        history=[],
    )

    assert result == expected_answer

    mock_answer_hr_question.assert_called_once_with(
        "How many sick leave days do employees receive?"
    )

    mock_crew_class.assert_not_called()