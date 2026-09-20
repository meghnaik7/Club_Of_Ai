import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

logger = logging.getLogger(__name__)

connect_args = {}
pool_kwargs = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    pool_kwargs = {"poolclass": NullPool}
else:
    pool_kwargs = {
        "pool_size": getattr(settings, "DB_POOL_SIZE", 10),
        "max_overflow": getattr(settings, "DB_MAX_OVERFLOW", 20),
        "pool_recycle": getattr(settings, "DB_POOL_RECYCLE", 300),
        "pool_timeout": getattr(settings, "DB_POOL_TIMEOUT", 30.0),
    }

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    **pool_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _auto_migrate_columns(target_engine):
    """Automatically adds newly defined columns if table already exists (for SQLite/Postgres dev)."""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(target_engine)
        with target_engine.connect() as conn:
            table_names = inspector.get_table_names()
            if "users" in table_names:
                user_cols = [c["name"] for c in inspector.get_columns("users")]
                if "club_id" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN club_id INTEGER"))
                if "subteam_id" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN subteam_id INTEGER"))
                if "username" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR"))
                if "phone" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR"))
                if "avatar_url" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR"))
                if "bio" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN bio TEXT"))
                if "skills" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN skills VARCHAR"))
                if "availability" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN availability VARCHAR"))
                if "created_at" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP"))

            if "teams" in table_names:
                team_cols = [c["name"] for c in inspector.get_columns("teams")]
                if "lead_id" not in team_cols:
                    conn.execute(text("ALTER TABLE teams ADD COLUMN lead_id INTEGER"))

            if "volunteers" in table_names:
                vol_cols = [c["name"] for c in inspector.get_columns("volunteers")]
                if "club_id" not in vol_cols:
                    conn.execute(text("ALTER TABLE volunteers ADD COLUMN club_id INTEGER"))
                if "subteam_id" not in vol_cols:
                    conn.execute(text("ALTER TABLE volunteers ADD COLUMN subteam_id INTEGER"))

            if "events" in table_names:
                event_cols = [c["name"] for c in inspector.get_columns("events")]
                if "club_id" not in event_cols:
                    conn.execute(text("ALTER TABLE events ADD COLUMN club_id INTEGER"))

            conn.commit()
    except Exception as exc:
        logger.warning(f"Auto-migration check notice: {exc}")


def init_db():
    """
    Initializes tables in the persistent production database.
    In production, connects to PostgreSQL and creates all tables, indexes, and seeded permissions.
    In development, gracefully falls back to local SQLite if PostgreSQL is offline and ALLOW_SQLITE_FALLBACK=True.
    """
    global engine, SessionLocal
    from app.db.base import Base as AppBase
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        AppBase.metadata.create_all(bind=engine)
        _auto_migrate_columns(engine)
        db_kind = "PostgreSQL" if "postgresql" in str(engine.url) else "Database"
        logger.info(
            f"[{db_kind} Active] Tables initialized & persistent at: "
            f"{engine.url.host or 'localhost'}:{engine.url.port or ''}/{engine.url.database or ''}"
        )
        from app.core.permissions import seed_permissions
        with SessionLocal() as db_session:
            seed_permissions(db_session)
    except Exception as e:
        if settings.ALLOW_SQLITE_FALLBACK and not str(engine.url).startswith("sqlite"):
            logger.warning(
                f"[Dev Fallback Notice] Could not connect to PostgreSQL at {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT} ({e}). "
                "ALLOW_SQLITE_FALLBACK is True: using local SQLite for development temporarily. "
                "For production persistence, ensure PostgreSQL is running and set ALLOW_SQLITE_FALLBACK=false."
            )
            sqlite_path = settings.BASE_DIR / "clubops.db"
            engine = create_engine(
                f"sqlite:///{sqlite_path.as_posix()}",
                connect_args={"check_same_thread": False},
                poolclass=NullPool
            )
            SessionLocal.configure(bind=engine)
            AppBase.metadata.create_all(bind=engine)
            _auto_migrate_columns(engine)
            from app.core.permissions import seed_permissions
            with SessionLocal() as db_session:
                seed_permissions(db_session)
        else:
            logger.error(f"[FATAL DATABASE ERROR] Failed to connect to persistent database at {engine.url}: {e}")
            raise e

