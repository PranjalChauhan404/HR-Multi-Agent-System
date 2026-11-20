from src.tools import (
    check_leave_balance,
    apply_for_leave,
    view_leave_requests,
    approve_leave_request,
    reject_leave_request,
)


def test_check_leave_balance():
    result = check_leave_balance(4, current_user_id=4)

    assert result["success"] is True
    assert "casual" in result["balances"]
    assert "sick" in result["balances"]
    assert "earned" in result["balances"]


def test_invalid_leave_type():
    result = apply_for_leave(
        4, "vacation", "2099-01-10", "2099-01-11",
        current_user_id=4,
    )
    assert result["success"] is False
    assert "Invalid leave type" in result["message"]


def test_invalid_date_range():
    result = apply_for_leave(
        4, "casual", "2099-01-12", "2099-01-10",
        current_user_id=4,
    )
    assert result["success"] is False
    assert "End date cannot be before start date" in result["message"]


def test_insufficient_leave_balance():
    result = apply_for_leave(
        4, "casual", "2099-01-01", "2099-01-31",
        current_user_id=4,
    )
    assert result["success"] is False
    assert "Insufficient leave balance" in result["message"]


def test_view_leave_requests():
    result = view_leave_requests(4, current_user_id=4)

    assert result["success"] is True
    assert isinstance(result["requests"], list)


def test_employee_cannot_approve_own_request():
    result = approve_leave_request(4, -1)
    assert result["success"] is False


def test_unknown_request_cannot_be_approved():
    result = approve_leave_request(2, -1)
    assert result["success"] is False
    assert "not found" in result["message"].lower()


def test_unknown_request_cannot_be_rejected():
    result = reject_leave_request(2, -1)
    assert result["success"] is False
    assert "not found" in result["message"].lower()