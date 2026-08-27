"""Database engine, session factory and declarative base.

JU_FIX is a Monolithic MVC application backed by one relational database.
SQLite is used for local development and CI; the same SQLAlchemy models run
against PostgreSQL in deployment by changing ``DATABASE_URL`` only.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Declarative base class shared by every JU_FIX model."""


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and guarantee that it is closed.

    Yields:
        Session: An active SQLAlchemy session bound to the request scope.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create every table declared on ``Base``.

    Importing ``app.models`` first guarantees that all model modules have been
    evaluated and registered on the metadata before the tables are created.
    """
    import app.models  # noqa: F401  (import for side effect: model registration)

    Base.metadata.create_all(bind=engine)
