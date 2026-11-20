from src.guardrails import (
    validate_user_role,
    validate_leave_request,
    can_view_employee_data,
    can_decide_leave_request,
)


def test_valid_roles():
    assert validate_user_role("employee")
    assert validate_user_role("manager")
    assert validate_user_role("hr_admin")
    assert not validate_user_role("admin")


def test_employee_can_view_own_data():
    assert can_view_employee_data(4, "employee", 4)


def test_employee_cannot_view_another_employee():
    assert not can_view_employee_data(4, "employee", 5)


def test_hr_admin_can_view_employee_data():
    assert can_view_employee_data(1, "hr_admin", 4)


def test_manager_can_view_direct_report():
    assert can_view_employee_data(
        2, "manager", 4, target_manager_id=2
    )


def test_manager_cannot_view_unassigned_employee():
    assert not can_view_employee_data(
        2, "manager", 4, target_manager_id=3
    )


def test_manager_can_decide_direct_report_leave():
    assert can_decide_leave_request(2, 4, "manager", 2)


def test_manager_cannot_decide_another_managers_leave():
    assert not can_decide_leave_request(2, 4, "manager", 3)


def test_employee_cannot_approve_leave():
    assert not can_decide_leave_request(4, 5, "employee", 4)


def test_invalid_leave_type():
    valid, message = validate_leave_request(
        "vacation", "2099-01-10", "2099-01-11"
    )
    assert not valid
    assert "Invalid leave type" in message


def test_end_date_before_start_date():
    valid, message = validate_leave_request(
        "casual", "2099-01-12", "2099-01-10"
    )
    assert not valid
    assert "End date cannot be before start date" in message