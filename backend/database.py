from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
from backend.config import DATABASE_URL

# PostgreSQL connection pool configuration
# For SQLite fallback, adjust connection args accordingly
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False
    )
else:
    # SQLite fallback
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
