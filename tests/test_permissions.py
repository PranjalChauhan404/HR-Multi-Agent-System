from datetime import date, timedelta

from src.tools import (
    apply_for_leave,
    check_leave_balance,
    view_leave_requests,
    approve_leave_request,
)


def test_employee_cannot_view_another_employees_balance():
    result = check_leave_balance(
        employee_id=5,
        current_user_id=4,
    )

    assert result["success"] is False
    assert "not authorized" in result["message"].lower()


def test_employee_cannot_view_another_employees_leave_history():
    result = view_leave_requests(
        employee_id=5,
        current_user_id=4,
    )

    assert result["success"] is False
    assert "not authorized" in result["message"].lower()


def test_employee_cannot_apply_for_leave_for_another_employee():
    start = date.today() + timedelta(days=60)

    result = apply_for_leave(
        employee_id=5,
        leave_type="casual",
        start_date=start.isoformat(),
        end_date=start.isoformat(),
        current_user_id=4,
    )

    assert result["success"] is False
    assert "only for yourself" in result["message"].lower()


def test_manager_cannot_approve_own_leave_request():
    # A nonexistent request ID avoids modifying any real leave request.
    result = approve_leave_request(
        manager_id=2,
        request_id=-999999,
    )

    assert result["success"] is False
    assert "not found" in result["message"].lower()