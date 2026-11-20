from unittest.mock import patch

import psycopg

from src.audit import log_action


@patch("src.audit.psycopg.connect")
def test_audit_log_success(mock_connect):
    mock_connection = mock_connect.return_value.__enter__.return_value
    mock_cursor = mock_connection.cursor.return_value.__enter__.return_value

    result = log_action(
        actor_id=4,
        action="leave_request_submitted",
        entity_type="leave_request",
        entity_id=10,
        details={"leave_type": "casual"},
    )

    assert result is True
    mock_cursor.execute.assert_called()


@patch(
    "src.audit.psycopg.connect",
    side_effect=psycopg.OperationalError("Database unavailable"),
)
def test_audit_log_failure(mock_connect):
    result = log_action(
        actor_id=4,
        action="audit_test",
        entity_type="system",
    )

    assert result is False
    mock_connect.assert_called_once()