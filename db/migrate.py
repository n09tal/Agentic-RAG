"""Apply the SQL files in db/migrations in order, each exactly once.

Usage:
    uv run python -m db.migrate
"""

import hashlib
from pathlib import Path

import psycopg

from backend.config import get_settings

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

CREATE_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    checksum   TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


class MigrationError(RuntimeError):
    pass


def checksum(sql_text: str) -> str:
    return hashlib.sha256(sql_text.encode("utf-8")).hexdigest()


def migrate(database_url: str, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    applied_now = []
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(CREATE_HISTORY_TABLE)
        applied = dict(conn.execute("SELECT version, checksum FROM schema_migrations").fetchall())

        for path in sorted(migrations_dir.glob("*.sql")):
            version = path.stem
            sql_text = path.read_text(encoding="utf-8")
            if version in applied:
                if applied[version] != checksum(sql_text):
                    raise MigrationError(f"{path.name} changed after it was applied. Add a new migration instead.")
                continue
            with conn.transaction():
                conn.execute(sql_text)
                conn.execute(
                    "INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)",
                    (version, checksum(sql_text)),
                )
            applied_now.append(version)
    return applied_now


def main() -> None:
    applied = migrate(get_settings().database_url)
    print(f"Applied: {', '.join(applied)}" if applied else "Database is up to date.")


if __name__ == "__main__":
    main()