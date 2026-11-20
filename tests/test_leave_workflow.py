from datetime import date, timedelta

import psycopg

from src.config import DATABASE_URL
from src.tools import apply_for_leave, approve_leave_request


def test_leave_application_approval_and_audit():
    employee_id = 4
    manager_id = 2
    leave_type = "casual"
    request_id = None
    approved = False

    start = date.today() + timedelta(days=30)
    end = start

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT remaining
                    FROM leave_balances
                    WHERE employee_id = %s AND leave_type = %s
                    """,
                    (employee_id, leave_type),
                )
                row = cur.fetchone()
                assert row is not None, "Leave balance record not found."
                balance_before = row[0]

                cur.execute("SELECT COUNT(*) FROM audit_log")
                audit_before = cur.fetchone()[0]

        assert balance_before >= 1

        # Submit leave request.
        result = apply_for_leave(
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            current_user_id=employee_id,
        )

        assert result["success"] is True, result
        request_id = result["request_id"]
        assert result["status"] == "pending"

        # Confirm request is pending.
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM leave_requests WHERE id = %s",
                    (request_id,),
                )
                assert cur.fetchone()[0] == "pending"

        # Approve request as the assigned manager.
        approval = approve_leave_request(
            manager_id=manager_id,
            request_id=request_id,
        )
        assert approval["success"] is True, approval
        assert approval["status"] == "approved"
        approved = True

        # Verify balance, final status, and audit records.
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT remaining
                    FROM leave_balances
                    WHERE employee_id = %s AND leave_type = %s
                    """,
                    (employee_id, leave_type),
                )
                balance_after = cur.fetchone()[0]

                cur.execute(
                    "SELECT status FROM leave_requests WHERE id = %s",
                    (request_id,),
                )
                assert cur.fetchone()[0] == "approved"

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM audit_log
                    WHERE action IN (
                        'leave_request_submitted',
                        'leave_request_approved'
                    )
                      AND details LIKE %s
                    """,
                    (f'%"entity_id": {request_id}%',),
                )
                workflow_audit_count = cur.fetchone()[0]

        assert balance_after == balance_before - 1
        assert workflow_audit_count >= 2

    finally:
        # Remove the test request and restore balance if approval succeeded.
        if request_id is not None:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    if approved:
                        cur.execute(
                            """
                            UPDATE leave_balances
                            SET remaining = remaining + 1
                            WHERE employee_id = %s AND leave_type = %s
                            """,
                            (employee_id, leave_type),
                        )

                    cur.execute(
                        "DELETE FROM leave_requests WHERE id = %s",
                        (request_id,),
                    )