from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")


def _sqlite_pragmas(dbapi_conn, connection_record):
    """SQLite-only: WAL mode + performance pragmas."""
    dbapi_conn.execute("PRAGMA journal_mode=WAL")
    dbapi_conn.execute("PRAGMA synchronous=NORMAL")
    dbapi_conn.execute("PRAGMA cache_size=-64000")
    dbapi_conn.execute("PRAGMA foreign_keys=ON")
    dbapi_conn.execute("PRAGMA temp_store=MEMORY")


def _make_engine():
    url = settings.database_url
    if url.startswith("sqlite"):
        eng = create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
        event.listen(eng, "connect", _sqlite_pragmas)
    else:
        # PostgreSQL (Supabase, Railway, etc.)
        eng = create_engine(
            url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,   # detect stale connections
            echo=False,
        )
    return eng


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
