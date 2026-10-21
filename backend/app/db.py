from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    if url.startswith("postgres://"):  # Render/Heroku style URLs
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("sqlite"):
        eng = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})

        @event.listens_for(eng, "connect")
        def _pragmas(conn, _):
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        return eng
    return create_engine(url, pool_pre_ping=True)


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def utcnow() -> datetime:
    """Naive UTC: SQLite has no timezone type, so all stored times are naive UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def init_db() -> None:
    from . import models  # noqa: F401  (registers tables)

    Base.metadata.create_all(engine)
    add_missing_columns()


def _column_default_sql(col) -> str:
    """A literal DEFAULT for a column added to an existing table, from its Python default."""
    arg = getattr(col.default, "arg", None)
    if callable(arg) or arg is None:
        arg = {"JSON": "{}"}.get(col.type.__class__.__name__)
        if arg is None:
            return ""
        return f" DEFAULT '{arg}'"
    if isinstance(arg, bool):
        return " DEFAULT " + ("TRUE" if arg else "FALSE") if engine.dialect.name == "postgresql" else f" DEFAULT {int(arg)}"
    if isinstance(arg, (int, float)):
        return f" DEFAULT {arg}"
    if isinstance(arg, (dict, list)):
        import json
        return f" DEFAULT '{json.dumps(arg)}'"
    return " DEFAULT '" + str(arg).replace("'", "''") + "'"


def add_missing_columns() -> list[str]:
    """create_all never alters existing tables. Add new nullable/defaulted columns so an older
    SQLite file or Postgres volume keeps working after an upgrade (no Alembic needed for additive changes)."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    added = []
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                ddl = f'ALTER TABLE {table.name} ADD COLUMN {col.name} {col.type.compile(engine.dialect)}{_column_default_sql(col)}'
                conn.execute(text(ddl))
                added.append(f"{table.name}.{col.name}")
    return added
