import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "..", "clubops.db")

def migrate():
    if not os.path.exists(db_path):
        print(f"No sqlite db at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check tasks table columns
    cur.execute("PRAGMA table_info(tasks)")
    cols = [r[1] for r in cur.fetchall()]
    print(f"Existing tasks columns: {cols}")

    if "team_id" not in cols:
        print("Adding team_id column to tasks...")
        cur.execute("ALTER TABLE tasks ADD COLUMN team_id INTEGER REFERENCES teams(id)")
    if "created_by" not in cols:
        print("Adding created_by column to tasks...")
        cur.execute("ALTER TABLE tasks ADD COLUMN created_by INTEGER REFERENCES users(id)")

    # Check audit_logs columns
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(audit_logs)")
        audit_cols = [r[1] for r in cur.fetchall()]
        print(f"Existing audit_logs columns: {audit_cols}")

        if "actor_id" not in audit_cols:
            print("Adding actor_id to audit_logs...")
            cur.execute("ALTER TABLE audit_logs ADD COLUMN actor_id INTEGER REFERENCES users(id)")
        if "scope_type" not in audit_cols:
            print("Adding scope_type to audit_logs...")
            cur.execute("ALTER TABLE audit_logs ADD COLUMN scope_type VARCHAR(50)")
        if "scope_id" not in audit_cols:
            print("Adding scope_id to audit_logs...")
            cur.execute("ALTER TABLE audit_logs ADD COLUMN scope_id INTEGER")
        if "meta_data" not in audit_cols:
            print("Adding meta_data to audit_logs...")
            cur.execute("ALTER TABLE audit_logs ADD COLUMN meta_data JSON")

    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
