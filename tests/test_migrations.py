import shutil

import psycopg
import pytest

from db.migrate import MIGRATIONS_DIR, MigrationError, migrate

PRODUCT = "INSERT INTO products (parent_asin, title) VALUES ('P1', 'Headphones')"
REVIEW = """
INSERT INTO reviews (review_id, parent_asin, asin, rating, reviewed_at, title, body,
                     verified_purchase, review_language, language_approved, snapshot_id,
                     source_file, source_line)
VALUES (%(review_id)s, 'P1', 'P1', %(rating)s, now(), 'Title', 'Great sound.',
        true, %(language)s, true, 'demo-test', 'reviews.jsonl.gz', %(line)s)
"""


def insert_review(conn, review_id="r_1", rating=5, language="en", line=1):
    conn.execute(REVIEW, {"review_id": review_id, "rating": rating, "language": language, "line": line})


def test_migrations_create_the_core_tables(fresh_database_url):
    assert migrate(fresh_database_url) == ["0001_extensions", "0002_core_tables"]

    with psycopg.connect(fresh_database_url) as conn:
        tables = {row[0] for row in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )}
    assert {"products", "reviews", "review_chunks", "review_aspects", "schema_migrations"} <= tables


def test_running_migrations_again_changes_nothing(fresh_database_url):
    migrate(fresh_database_url)

    assert migrate(fresh_database_url) == []


def test_editing_an_applied_migration_is_rejected(fresh_database_url, tmp_path):
    migrations = tmp_path / "migrations"
    shutil.copytree(MIGRATIONS_DIR, migrations)
    migrate(fresh_database_url, migrations)
    with (migrations / "0002_core_tables.sql").open("a", encoding="utf-8") as f:
        f.write("\n-- edited\n")

    with pytest.raises(MigrationError, match="0002_core_tables.sql changed"):
        migrate(fresh_database_url, migrations)


def test_constraints_reject_bad_rows(fresh_database_url):
    migrate(fresh_database_url)
    with psycopg.connect(fresh_database_url, autocommit=True) as conn:
        conn.execute(PRODUCT)
        insert_review(conn)

        with pytest.raises(psycopg.errors.CheckViolation):
            insert_review(conn, review_id="r_2", rating=6, line=2)
        with pytest.raises(psycopg.errors.CheckViolation):
            insert_review(conn, review_id="r_3", language="es", line=3)
        with pytest.raises(psycopg.errors.UniqueViolation):
            insert_review(conn, review_id="r_4", line=1)

        chunk = """INSERT INTO review_chunks (chunk_id, review_id, chunk_no, char_start, char_end, chunk_text)
                   VALUES (%s, 'r_1', 1, 0, 5, 'Great')"""
        conn.execute(chunk, ("r_1:1",))
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(chunk, ("r_1:1-duplicate",))