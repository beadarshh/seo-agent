import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from config import settings
from db.database import SETUP_SQL

def setup():
    print("Connecting to Supabase PostgreSQL...")
    try:
        conn = psycopg2.connect(settings.SUPABASE_DB_URL)
        cur = conn.cursor()
        print("Executing setup SQL...")
        cur.execute(SETUP_SQL)
        conn.commit()
        cur.close()
        conn.close()
        print("Database setup complete!")
    except Exception as e:
        print(f"Error setting up database: {e}")

if __name__ == "__main__":
    setup()
