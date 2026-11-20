from datetime import date, timedelta

import psycopg

from src.config import DATABASE_URL
from src.tools import apply_for_leave, approve_leave_request


def create_test_request(employee_id, leave_type="casual"):
    """Create a temporary pending request for authorization tests."""
    start = date.today() + timedelta(days=90)

    result = apply_for_leave(
        employee_id=employee_id,
        leave_type=leave_type,
        start_date=start.isoformat(),
        end_date=start.isoformat(),
        current_user_id=employee_id,
    )

    assert result["success"], result
    return result["request_id"]


def delete_test_request(request_id):
    """Delete only the temporary request created by the test."""
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM leave_requests WHERE id = %s",
                (request_id,),
            )


def test_manager_cannot_approve_own_leave_request():
    # Rahul (2) is a manager. Create a request for Rahul himself.
    request_id = create_test_request(employee_id=2)

    try:
        result = approve_leave_request(
            manager_id=2,
            request_id=request_id,
        )

        assert result["success"] is False
        assert "own requests" in result["message"].lower()

        # The request must remain pending.
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM leave_requests WHERE id = %s",
                    (request_id,),
                )
                assert cur.fetchone()[0] == "pending"
    finally:
        delete_test_request(request_id)


def test_manager_cannot_approve_non_direct_report_request():
    # Arjun (4) reports to Rahul (2), not Sneha (3).
    request_id = create_test_request(employee_id=4)

    try:
        result = approve_leave_request(
            manager_id=3,
            request_id=request_id,
        )

        assert result["success"] is False
        assert "assigned manager" in result["message"].lower()

        # The request must remain pending.
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM leave_requests WHERE id = %s",
                    (request_id,),
                )
                assert cur.fetchone()[0] == "pending"
    finally:
        delete_test_request(request_id)