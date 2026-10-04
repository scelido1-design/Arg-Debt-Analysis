import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    return psycopg.connect(
        host=os.getenv("PGHOST"), port=os.getenv("PGPORT"),
        dbname=os.getenv("PGDATABASE"), user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"))

if __name__ == "__main__":
    with get_conn() as conn:
        print(conn.execute("SELECT version()").fetchone()[0])