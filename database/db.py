"""Gerenciamento centralizado de conexão e inicialização do banco SQLite."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
DEFAULT_DB_PATH = ROOT / "database" / "vulcantech.db"


def resolve_sqlite_path(database_url: str | None = None) -> Path:
    """Resolve o caminho do arquivo SQLite a partir de DATABASE_URL ou usa o padrão."""
    raw = (database_url or os.getenv("DATABASE_URL") or "").strip()
    if not raw:
        return DEFAULT_DB_PATH
    if raw.startswith("sqlite:///"):
        path_part = raw.removeprefix("sqlite:///")
        path = Path(path_part)
        return path if path.is_absolute() else (ROOT / path).resolve()
    path = Path(raw)
    return path if path.is_absolute() else (ROOT / path).resolve()


def get_connection(database_url: str | None = None) -> sqlite3.Connection:
    """Abre conexão SQLite configurada com Row factory, WAL e timeout seguro."""
    db_path = resolve_sqlite_path(database_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


@contextmanager
def db_session(database_url: str | None = None) -> Iterator[sqlite3.Connection]:
    """Context manager transacional para operações no SQLite."""
    conn = get_connection(database_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(database_url: str | None = None) -> Path:
    """Executa schema.sql de maneira idempotente e retorna o caminho do banco."""
    db_path = resolve_sqlite_path(database_url)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with db_session(database_url) as conn:
        conn.executescript(schema_sql)
    return db_path


def check_db_health(database_url: str | None = None) -> dict[str, object]:
    """Verifica conectividade e existência das tabelas principais sem expor segredos."""
    try:
        db_path = resolve_sqlite_path(database_url)
        with db_session(database_url) as conn:
            row = conn.execute("SELECT 1 AS ok;").fetchone()
            tables = [
                r["name"]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
                ).fetchall()
            ]
        return {
            "available": bool(row and row["ok"] == 1),
            "engine": "sqlite",
            "database_file": db_path.name,
            "tables": sorted(tables),
            "error": None,
        }
    except Exception as error:
        return {
            "available": False,
            "engine": "sqlite",
            "database_file": None,
            "tables": [],
            "error": str(error),
        }

