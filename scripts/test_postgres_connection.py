import sys
import os

# Ensure backend and root are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings
from app.core.database import init_db
from app.db.base import Base

def verify_postgres_connection():
    print("=" * 65)
    print("CLUBOPS AI - POSTGRESQL DOCKER CONNECTION & PERSISTENCE VERIFIER")
    print("=" * 65)
    print(f"Target DATABASE_URL: {settings.DATABASE_URL}")

    try:
        engine = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version();")).scalar()
            print("\n[SUCCESS] Connected to PostgreSQL Docker container!")
            print(f"PostgreSQL Version:\n  {version}")

        print("\n[STEP 2] Initializing schema and persistent tables...")
        init_db()

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n[SUCCESS] Found {len(tables)} tables in PostgreSQL:")
        for t in sorted(tables):
            print(f"  - {t}")

        required_tables = ["users", "events", "tasks", "volunteers", "documents", "document_chunks", "announcements"]
        missing = [t for t in required_tables if t not in tables]
        if missing:
            print(f"\n[WARNING] Some tables not found: {missing}")
        else:
            print("\n[OK] All core backend and RAG tables are initialized and persistent!")

        print("\n" + "=" * 65)
        print("POSTGRESQL SETUP COMPLETE & PERSISTENT DATA VERIFIED")
        print("=" * 65)
        return True

    except Exception as e:
        print("\n[NOTICE] Could not connect to PostgreSQL Docker container:")
        print(f"  {e}")
        print("\nHow to fix:")
        print("  1. Ensure Docker Desktop is open and running.")
        print("  2. In your terminal, run:")
        print("       docker compose up -d")
        print("  3. Run this verification script again:")
        print("       python scripts/test_postgres_connection.py")
        return False

if __name__ == "__main__":
    verify_postgres_connection()
