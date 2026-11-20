from datetime import date

import psycopg

from src.config import DATABASE_URL
from src.guardrails import validate_leave_request
from src.audit import log_action


VALID_LEAVE_TYPES = {"casual", "sick", "earned"}


def _get_employee_role(cur, employee_id: int):
    """Retrieve an employee's role from the database."""
    cur.execute(
        "SELECT role FROM employees WHERE id = %s",
        (employee_id,),
    )
    row = cur.fetchone()
    return row[0] if row else None


def _is_authorized_employee(
    cur,
    current_user_id: int,
    target_employee_id: int,
) -> bool:
    """Employees access their own records; HR admins may access all."""
    role = _get_employee_role(cur, current_user_id)

    if role == "hr_admin":
        return True

    return (
        role in {"employee", "manager"}
        and current_user_id == target_employee_id
    )


def check_leave_balance(
    employee_id: int,
    current_user_id: int | None = None,
) -> dict:
    """Return leave balances after verifying the caller's permissions."""

    if current_user_id is None:
        return {
            "success": False,
            "message": "Authenticated user identity is required.",
        }

    with psycopg.connect(DATABASE_URL, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            if not _is_authorized_employee(
                cur, current_user_id, employee_id
            ):
                return {
                    "success": False,
                    "message": "You are not authorized to view these balances.",
                }

            cur.execute(
                """
                SELECT leave_type, remaining
                FROM leave_balances
                WHERE employee_id = %s
                ORDER BY leave_type
                """,
                (employee_id,),
            )
            rows = cur.fetchall()

    if not rows:
        return {
            "success": False,
            "message": "No leave balance records found for this employee.",
        }

    log_action(
        actor_id=current_user_id,
        action="leave_balance_viewed",
        entity_type="employee",
        entity_id=employee_id,
    )

    return {
        "success": True,
        "employee_id": employee_id,
        "balances": {
            leave_type: remaining
            for leave_type, remaining in rows
        },
    }


def apply_for_leave(
    employee_id: int,
    leave_type: str,
    start_date: str,
    end_date: str,
    current_user_id: int | None = None,
) -> dict:
    """Submit a leave request only for the authenticated employee."""

    if current_user_id is None or current_user_id != employee_id:
        return {
            "success": False,
            "message": "You can submit leave requests only for yourself.",
        }

    if not isinstance(leave_type, str):
        return {
            "success": False,
            "message": "Invalid leave type.",
        }

    leave_type = leave_type.strip().lower()

    if leave_type.endswith(" leave"):
        leave_type = leave_type[:-6].strip()

    if leave_type not in VALID_LEAVE_TYPES:
        return {
            "success": False,
            "message": "Invalid leave type. Use casual, sick, or earned.",
        }

    valid, message = validate_leave_request(
        leave_type,
        start_date,
        end_date,
    )

    if not valid:
        return {
            "success": False,
            "message": message,
        }

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    requested_days = (end - start).days + 1

    with psycopg.connect(DATABASE_URL, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            role = _get_employee_role(cur, current_user_id)

            if role not in {"employee", "manager"}:
                return {
                    "success": False,
                    "message": (
                        "Only employees and managers can submit leave requests."
                    ),
                }

            cur.execute(
                """
                SELECT remaining
                FROM leave_balances
                WHERE employee_id = %s AND leave_type = %s
                FOR UPDATE
                """,
                (employee_id, leave_type),
            )
            balance_row = cur.fetchone()

            if balance_row is None:
                return {
                    "success": False,
                    "message": "No balance record found for this leave type.",
                }

            if requested_days > balance_row[0]:
                return {
                    "success": False,
                    "message": (
                        f"Insufficient leave balance. Available: "
                        f"{balance_row[0]} days; requested: "
                        f"{requested_days} days."
                    ),
                }

            cur.execute(
                """
                SELECT id
                FROM leave_requests
                WHERE employee_id = %s
                  AND status IN ('pending', 'approved')
                  AND start_date <= %s
                  AND end_date >= %s
                LIMIT 1
                """,
                (employee_id, end, start),
            )

            if cur.fetchone():
                return {
                    "success": False,
                    "message": (
                        "These dates overlap an existing pending "
                        "or approved leave request."
                    ),
                }

            cur.execute(
                """
                INSERT INTO leave_requests
                    (employee_id, leave_type, start_date, end_date, status)
                VALUES (%s, %s, %s, %s, 'pending')
                RETURNING id
                """,
                (employee_id, leave_type, start, end),
            )

            request_id = cur.fetchone()[0]

    # The database transaction has committed before audit logging.
    log_action(
        actor_id=current_user_id,
        action="leave_request_submitted",
        entity_type="leave_request",
        entity_id=request_id,
        details={
            "leave_type": leave_type,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "requested_days": requested_days,
        },
    )

    return {
        "success": True,
        "request_id": request_id,
        "status": "pending",
        "requested_days": requested_days,
        "message": "Leave request submitted for manager approval.",
    }


def view_leave_requests(
    employee_id: int,
    current_user_id: int | None = None,
) -> dict:
    """Return leave history after verifying the caller's permissions."""

    if current_user_id is None:
        return {
            "success": False,
            "message": "Authenticated user identity is required.",
        }

    with psycopg.connect(DATABASE_URL, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            if not _is_authorized_employee(
                cur, current_user_id, employee_id
            ):
                log_action(
                    actor_id=current_user_id,
                    action="unauthorized_leave_balance_access",
                    entity_type="employee",
                    entity_id=employee_id,
                )
                return {
                    "success": False,
                    "message": "You are not authorized to view these balances.",
                }

            cur.execute(
                """
                SELECT id, leave_type, start_date, end_date, status, created_at
                FROM leave_requests
                WHERE employee_id = %s
                ORDER BY created_at DESC, id DESC
                """,
                (employee_id,),
            )
            rows = cur.fetchall()

    log_action(
        actor_id=current_user_id,
        action="leave_requests_viewed",
        entity_type="employee",
        entity_id=employee_id,
    )

    return {
        "success": True,
        "employee_id": employee_id,
        "requests": [
            {
                "request_id": row[0],
                "leave_type": row[1],
                "start_date": row[2].isoformat(),
                "end_date": row[3].isoformat(),
                "status": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
            }
            for row in rows
        ],
    }



def view_team_members(manager_id: int) -> dict:
    """Return only the authenticated manager's direct reports."""
    with psycopg.connect(DATABASE_URL, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            if _get_employee_role(cur, manager_id) != "manager":
                return {"success": False, "message": "Only managers can view team members."}
            cur.execute(
                """SELECT id, name, email, department, role
                   FROM employees WHERE manager_id = %s
                   ORDER BY name, id""",
                (manager_id,),
            )
            rows = cur.fetchall()
    log_action(actor_id=manager_id, action="team_directory_viewed",
               entity_type="employee", entity_id=manager_id)
    members = [{"employee_id": r[0], "name": r[1], "email": r[2],
                "department": r[3], "role": r[4]} for r in rows]
    return {"success": True, "manager_id": manager_id, "members": members,
            "message": f"Found {len(members)} direct report(s)."}

def view_team_members_without_leave_requests(manager_id: int) -> dict:
    """List direct reports who have never submitted a leave request."""
    with psycopg.connect(DATABASE_URL, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            if _get_employee_role(cur, manager_id) != "manager":
                return {"success": False, "message": "Only managers can view team leave analytics."}
            cur.execute(
                """SELECT e.id, e.name, e.department, e.role
                   FROM employees e
                   LEFT JOIN leave_requests lr ON lr.employee_id = e.id
                   WHERE e.manager_id = %s
                   GROUP BY e.id, e.name, e.department, e.role
                   HAVING COUNT(lr.id) = 0
                   ORDER BY e.name, e.id""",
                (manager_id,),
            )
            rows = cur.fetchall()
    log_action(actor_id=manager_id, action="team_leave_history_analytics_viewed",
               entity_type="employee", entity_id=manager_id)
    members = [{"employee_id": r[0], "name": r[1], "department": r[2], "role": r[3]} for r in rows]
    return {"success": True, "members": members,
            "message": f"Found {len(members)} team member(s) with no leave requests."}

def view_team_pending_requests(manager_id: int) -> dict:
    """List pending leave requests belonging to a manager's direct reports."""

    with psycopg.connect(DATABASE_URL, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            # Only managers can retrieve their team's pending requests.
            if _get_employee_role(cur, manager_id) != "manager":
                return {
                    "success": False,
                    "message": "Only managers can view team pending requests.",
                }

            cur.execute(
                """
                SELECT
                    lr.id,
                    lr.employee_id,
                    lr.leave_type,
                    lr.start_date,
                    lr.end_date,
                    lr.status,
                    lr.created_at
                FROM leave_requests AS lr
                JOIN employees AS e
                    ON e.id = lr.employee_id
                WHERE e.manager_id = %s
                  AND lr.status = 'pending'
                ORDER BY lr.created_at ASC, lr.id ASC
                """,
                (manager_id,),
            )

            rows = cur.fetchall()

    log_action(
        actor_id=manager_id,
        action="team_pending_requests_viewed",
        entity_type="employee",
        entity_id=manager_id,
    )

    requests = [
        {
            "request_id": row[0],
            "employee_id": row[1],
            "leave_type": row[2],
            "start_date": row[3].isoformat(),
            "end_date": row[4].isoformat(),
            "status": row[5],
            "created_at": row[6].isoformat() if row[6] else None,
        }
        for row in rows
    ]

    return {
        "success": True,
        "manager_id": manager_id,
        "requests": requests,
        "message": (
            f"Found {len(requests)} pending team request(s)."
            if requests
            else "No pending leave requests for your team."
        ),
    }

def view_team_leave_balances(manager_id: int) -> dict:
    """View leave balances for a manager's direct reports."""
    with psycopg.connect(DATABASE_URL, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            if _get_employee_role(cur, manager_id) != "manager":
                return {
                    "success": False,
                    "message": "Only managers can view team leave balances.",
                }

            cur.execute(
                """
                SELECT e.id, lb.leave_type, lb.remaining
                FROM employees AS e
                JOIN leave_balances AS lb
                    ON lb.employee_id = e.id
                WHERE e.manager_id = %s
                ORDER BY e.id, lb.leave_type
                """,
                (manager_id,),
            )
            rows = cur.fetchall()

    balances = [
        {
            "employee_id": row[0],
            "leave_type": row[1],
            "remaining": row[2],
        }
        for row in rows
    ]

    return {
        "success": True,
        "manager_id": manager_id,
        "balances": balances,
        "message": (
            f"Found {len(balances)} team leave balance record(s)."
            if balances
            else "No leave balances found for your team."
        ),
    }

def _process_leave_decision(
    manager_id: int,
    request_id: int,
    decision: str,
) -> dict:
    """Approve or reject a request after checking manager authorization."""

    if decision not in {"approved", "rejected"}:
        return {
            "success": False,
            "message": "Invalid decision.",
        }

    with psycopg.connect(DATABASE_URL, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT employee_id, leave_type, start_date, end_date, status
                FROM leave_requests
                WHERE id = %s
                FOR UPDATE
                """,
                (request_id,),
            )

            request = cur.fetchone()

            if request is None:
                return {
                    "success": False,
                    "message": "Leave request not found.",
                }

            employee_id, leave_type, start, end, status = request

            if employee_id == manager_id:
                return {
                    "success": False,
                    "message": "Managers cannot decide their own requests.",
                }

            if _get_employee_role(cur, manager_id) != "manager":
                return {
                    "success": False,
                    "message": (
                        "Only authorized managers can decide leave requests."
                    ),
                }

            cur.execute(
                """
                SELECT 1
                FROM employees
                WHERE id = %s AND manager_id = %s
                """,
                (employee_id, manager_id),
            )

            if cur.fetchone() is None:
                return {
                    "success": False,
                    "message": (
                        "You are not this employee's assigned manager."
                    ),
                }

            if status != "pending":
                return {
                    "success": False,
                    "message": f"This request is already {status}.",
                }

            requested_days = (end - start).days + 1

            if decision == "approved":
                cur.execute(
                    """
                    SELECT remaining
                    FROM leave_balances
                    WHERE employee_id = %s AND leave_type = %s
                    FOR UPDATE
                    """,
                    (employee_id, leave_type),
                )

                balance = cur.fetchone()

                if balance is None or balance[0] < requested_days:
                    return {
                        "success": False,
                        "message": (
                            "Insufficient leave balance to approve this request."
                        ),
                    }

                cur.execute(
                    """
                    UPDATE leave_balances
                    SET remaining = remaining - %s
                    WHERE employee_id = %s AND leave_type = %s
                    """,
                    (requested_days, employee_id, leave_type),
                )

            cur.execute(
                """
                UPDATE leave_requests
                SET status = %s
                WHERE id = %s
                """,
                (decision, request_id),
            )

    # Record the decision after the transaction commits.
    log_action(
        actor_id=manager_id,
        action=f"leave_request_{decision}",
        entity_type="leave_request",
        entity_id=request_id,
        details={
            "employee_id": employee_id,
            "requested_days": requested_days,
        },
    )

    return {
        "success": True,
        "request_id": request_id,
        "status": decision,
        "message": f"Leave request {decision} successfully.",
    }


def approve_leave_request(manager_id: int, request_id: int) -> dict:
    """Approve a pending request belonging to a direct report."""
    return _process_leave_decision(
        manager_id,
        request_id,
        "approved",
    )


def reject_leave_request(manager_id: int, request_id: int) -> dict:
    """Reject a pending request belonging to a direct report."""
    return _process_leave_decision(
        manager_id,
        request_id,
        "rejected",
    )


if __name__ == "__main__":
    print("Security check: missing identity must be rejected.")
    print(check_leave_balance(4))
    print(view_leave_requests(4))