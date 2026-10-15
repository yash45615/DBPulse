"""Database engine, health checks, schema initialization, and migrations."""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for DBPulse ORM models."""


def create_database_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine for the configured database."""
    if not database_url.strip():
        raise ValueError("Database URL must not be empty")

    engine_options: dict = {"pool_pre_ping": True}

    if database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}

    return create_engine(database_url, **engine_options)


def check_database_connection(engine: Engine) -> bool:
    """Return True if the database responds to a simple query."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return result.scalar_one() == 1


def migrate_benchmark_run_metadata(engine: Engine) -> None:
    """Add metadata_json to existing benchmark_runs tables when needed."""
    inspector = inspect(engine)

    if not inspector.has_table("benchmark_runs"):
        return

    columns = {column["name"] for column in inspector.get_columns("benchmark_runs")}

    if "metadata_json" in columns:
        return

    if engine.dialect.name == "postgresql":
        statement = """
            ALTER TABLE benchmark_runs
            ADD COLUMN metadata_json JSON NOT NULL DEFAULT '{}'::json
        """
    elif engine.dialect.name == "sqlite":
        statement = """
            ALTER TABLE benchmark_runs
            ADD COLUMN metadata_json JSON NOT NULL DEFAULT '{}'
        """
    else:
        raise ValueError(
            "Adding benchmark metadata is not supported for database "
            f"dialect {engine.dialect.name!r}"
        )

    with engine.begin() as connection:
        connection.execute(text(statement))


def initialize_schema(engine: Engine) -> None:
    """Create missing tables and migrate existing benchmark run metadata."""
    # Import models so their tables are registered with Base.metadata.
    from dbpulse import models  # noqa: F401

    Base.metadata.create_all(engine)
    migrate_benchmark_run_metadata(engine)
