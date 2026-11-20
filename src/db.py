import psycopg
from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path, override=True)

DATABASE_URL = os.getenv("DATABASE_URL")


def seed_database():
    employees = [
        ("Priya Sharma", "priya@company.com", "hr_admin", "Human Resources", None),
        ("Rahul Mehta", "rahul@company.com", "manager", "Engineering", 1),
        ("Sneha Patel", "sneha@company.com", "manager", "Marketing", 1),
        ("Arjun Desai", "arjun@company.com", "employee", "Engineering", 2),
        ("Neha Joshi", "neha@company.com", "employee", "Engineering", 2),
        ("Karan Shah", "karan@company.com", "employee", "Marketing", 3),
        ("Aditi Kulkarni", "aditi@company.com", "employee", "Marketing", 3),
    ]

    leave_types = {
        "casual": 12,
        "sick": 10,
        "earned": 15,
    }

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Avoid duplicate records if the script is rerun.
            cur.execute("SELECT COUNT(*) FROM employees")
            if cur.fetchone()[0] > 0:
                print("Database already contains employees. Seeding skipped.")
                return

            employee_ids = []

            for name, email, role, department, manager_id in employees:
                cur.execute(
                    """
                    INSERT INTO employees
                        (name, email, role, department, manager_id)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (name, email, role, department, manager_id),
                )
                employee_ids.append(cur.fetchone()[0])

            for employee_id in employee_ids:
                for leave_type, balance in leave_types.items():
                    cur.execute(
                        """
                        INSERT INTO leave_balances
                            (employee_id, leave_type, remaining)
                        VALUES (%s, %s, %s)
                        """,
                        (employee_id, leave_type, balance),
                    )

    print("Database seeded successfully!")
    print(f"Employees created: {len(employees)}")
    print(f"Leave balances created: {len(employees) * len(leave_types)}")


if __name__ == "__main__":
    seed_database()