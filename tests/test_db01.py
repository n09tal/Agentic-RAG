"""DB-01: one English review with three chunks counts as one complaint.

R17 is the test alias of a real approved review (see tests/fixtures/r17.json):
two of its three chunks criticize the same aspect (pressure / pain around the ears).
"""

import json
from pathlib import Path

import psycopg
import pytest

from db.migrate import migrate
from ingest.db_writer import insert_aspect, insert_chunks, insert_review, review_row, upsert_product

R17 = json.loads((Path(__file__).parent / "fixtures" / "r17.json").read_text(encoding="utf-8"))
PARAMS = {
    "parent_asin": R17["product"]["parent_asin"],
    "aspect": R17["label"]["aspect"],
    "version": R17["label"]["label_version"],
}

COMPLAINTS = """
SELECT count(DISTINCT a.review_id)
FROM review_aspects a
JOIN reviews r USING (review_id)
WHERE r.parent_asin = %(parent_asin)s
  AND r.label_status = 'labeled' AND r.label_version = %(version)s
  AND a.label_version = %(version)s AND a.aspect = %(aspect)s AND a.sentiment = 'negative'
"""
LABELED = """
SELECT count(*) FROM reviews
WHERE parent_asin = %(parent_asin)s AND label_status = 'labeled' AND label_version = %(version)s
"""
NAIVE_COMPLAINTS = """
SELECT count(*)
FROM review_chunks c
JOIN review_aspects a USING (review_id)
WHERE a.aspect = %(aspect)s AND a.sentiment = 'negative'
"""


def load_r17(conn: psycopg.Connection) -> dict:
    review = R17["review"]
    return {
        "products": upsert_product(conn, R17["product"]),
        "reviews": insert_review(conn, review_row(review)),
        "chunks": insert_chunks(conn, review["review_id"], review["text"], R17["chunk_ranges"]),
        "aspects": insert_aspect(conn, R17["label"]),
    }


def count_rows(conn: psycopg.Connection) -> dict:
    return {
        table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in ("reviews", "review_chunks", "review_aspects")
    }


@pytest.fixture
def db(fresh_database_url):
    migrate(fresh_database_url)
    with psycopg.connect(fresh_database_url, autocommit=True) as conn:
        yield conn


def test_step1_load_one_review_three_chunks_one_label(db):
    load_r17(db)

    assert count_rows(db) == {"reviews": 1, "review_chunks": 3, "review_aspects": 1}
    mismatched = db.execute("""
        SELECT count(*) FROM review_chunks c JOIN reviews r USING (review_id)
        WHERE substr(r.body, c.char_start + 1, c.char_end - c.char_start) <> c.chunk_text
    """).fetchone()[0]
    assert mismatched == 0


def test_step2_two_excerpts_hit_two_chunks_of_the_same_review(db):
    load_r17(db)

    hits = [
        db.execute(
            "SELECT chunk_id, review_id FROM review_chunks WHERE strpos(chunk_text, %s) > 0", (excerpt,)
        ).fetchall()
        for excerpt in R17["negative_excerpts"]
    ]

    assert all(len(rows) == 1 for rows in hits)
    chunk_ids = {rows[0][0] for rows in hits}
    review_ids = {rows[0][1] for rows in hits}
    assert len(chunk_ids) == 2
    assert review_ids == {R17["review"]["review_id"]}


def test_step3_count_complaining_reviews_not_chunks(db):
    load_r17(db)

    complaints = db.execute(COMPLAINTS, PARAMS).fetchone()[0]
    labeled = db.execute(LABELED, PARAMS).fetchone()[0]
    naive = db.execute(NAIVE_COMPLAINTS, PARAMS).fetchone()[0]

    assert (complaints, labeled) == (1, 1)
    assert naive == 3


def test_step4_rerunning_the_import_changes_nothing(db):
    load_r17(db)

    second_run = load_r17(db)

    assert (second_run["reviews"], second_run["chunks"], second_run["aspects"]) == (0, 0, 0)
    assert count_rows(db) == {"reviews": 1, "review_chunks": 3, "review_aspects": 1}
    assert db.execute(COMPLAINTS, PARAMS).fetchone()[0] == 1