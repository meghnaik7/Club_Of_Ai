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

def init_db():
    """Initializes tables in database. Uses PostgreSQL container if running, with graceful offline fallback."""
    global engine, SessionLocal
    from app.db.base import Base as AppBase
    try:
        with engine.connect() as conn:
            pass
        AppBase.metadata.create_all(bind=engine)
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
            from app.core.permissions import seed_permissions
            with SessionLocal() as db_session:
                seed_permissions(db_session)
        else:
            raise e
