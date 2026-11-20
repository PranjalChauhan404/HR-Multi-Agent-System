import json
from datetime import datetime, timezone

import psycopg

from src.config import DATABASE_URL


def log_action(
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: dict | None = None,
) -> bool:
    """Record an audit event in PostgreSQL."""

    audit_details = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        **(details or {}),
    }

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_log
                        (user_id, action, details, timestamp)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        actor_id,
                        action,
                        json.dumps(audit_details),
                        datetime.now(timezone.utc),
                    ),
                )

        return True

    except psycopg.Error as exc:
        print(f"Audit logging failed: {exc}")
        return False


if __name__ == "__main__":
    success = log_action(
        actor_id=4,
        action="audit_test",
        entity_type="system",
        details={"message": "Audit logging test"},
    )
    print(f"Audit logging successful: {success}")