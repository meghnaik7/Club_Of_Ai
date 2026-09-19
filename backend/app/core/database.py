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
    """Initializes tables in database. Uses PostgreSQL container if running, with graceful offline fallback."""
    global engine, SessionLocal
    from app.db.base import Base as AppBase
    try:
        with engine.connect() as conn:
            pass
        AppBase.metadata.create_all(bind=engine)
        _auto_migrate_columns(engine)
        logger.info(f"Connected to PostgreSQL successfully! Tables created on {engine.url.host}:{engine.url.port}/{engine.url.database}")
        from app.core.permissions import seed_permissions
        with SessionLocal() as db_session:
            seed_permissions(db_session)
    except Exception as e:
        if not str(engine.url).startswith("sqlite"):
            logger.warning(
                f"[PostgreSQL Notice] Could not connect to PostgreSQL at {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT} ({e}). "
                "Ensure Docker container is running: 'docker compose up -d'. "
                "Falling back to local SQLite temporarily so app remains operational."
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
            raise e

