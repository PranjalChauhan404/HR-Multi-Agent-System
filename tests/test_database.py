import psycopg
from dotenv import load_dotenv
from pathlib import Path
import os

# Load .env from the project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path, override=True)

DATABASE_URL = os.getenv("DATABASE_URL")


def test_database_connection():
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database();")
                database_name = cur.fetchone()[0]

        print(f"✅ Connected successfully to: {database_name}")

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise


if __name__ == "__main__":
    test_database_connection()