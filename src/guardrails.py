from datetime import date

VALID_ROLES = {"employee", "manager", "hr_admin"}
VALID_LEAVE_TYPES = {"casual", "sick", "earned"}


def validate_user_role(role: str) -> bool:
    return role in VALID_ROLES


def validate_leave_request(
    leave_type: str,
    start_date: str,
    end_date: str,
) -> tuple[bool, str]:
    if not isinstance(leave_type, str) or leave_type.strip().lower() not in VALID_LEAVE_TYPES:
        return False, "Invalid leave type."

    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except (TypeError, ValueError):
        return False, "Dates must use YYYY-MM-DD format."

    if end < start:
        return False, "End date cannot be before start date."

    if start < date.today():
        return False, "Leave cannot be requested for dates in the past."

    return True, "Leave request is valid."


def can_view_employee_data(
    current_user_id: int,
    current_user_role: str,
    target_employee_id: int,
    target_manager_id: int | None = None,
) -> bool:
    if current_user_role not in VALID_ROLES:
        return False

    if current_user_role == "hr_admin":
        return True

    if current_user_id == target_employee_id:
        return True

    return (
        current_user_role == "manager"
        and target_manager_id == current_user_id
    )


def can_decide_leave_request(
    manager_id: int,
    employee_id: int,
    manager_role: str,
    assigned_manager_id: int | None,
) -> bool:
    return (
        manager_role == "manager"
        and manager_id != employee_id
        and assigned_manager_id == manager_id
    )