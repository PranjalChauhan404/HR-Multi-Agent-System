import psycopg
from src.config import DATABASE_URL

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'leave_balances'
            ORDER BY ordinal_position;
        """)

        for row in cur.fetchall():
            print(row)