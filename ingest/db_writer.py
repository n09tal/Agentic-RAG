"""Write rows into the core tables.

Every write is idempotent: running the same import again inserts nothing new.
"""

import psycopg

UPSERT_PRODUCT = """
INSERT INTO products (parent_asin, title, brand, model_number, category, recorded_price)
VALUES (%(parent_asin)s, %(title)s, %(brand)s, %(model_number)s, %(category)s, %(recorded_price)s)
ON CONFLICT (parent_asin) DO UPDATE SET
    title = EXCLUDED.title,
    brand = EXCLUDED.brand,
    model_number = EXCLUDED.model_number,
    category = EXCLUDED.category,
    recorded_price = EXCLUDED.recorded_price
"""

INSERT_REVIEW = """
INSERT INTO reviews (review_id, parent_asin, asin, rating, reviewed_at, title, body, helpful_vote,
                     verified_purchase, review_language, language_approved, snapshot_id,
                     source_file, source_line)
VALUES (%(review_id)s, %(parent_asin)s, %(asin)s, %(rating)s, %(reviewed_at)s, %(title)s, %(body)s,
        %(helpful_vote)s, %(verified_purchase)s, %(review_language)s, %(language_approved)s,
        %(snapshot_id)s, %(source_file)s, %(source_line)s)
ON CONFLICT DO NOTHING
"""

INSERT_CHUNK = """
INSERT INTO review_chunks (chunk_id, review_id, chunk_no, char_start, char_end, chunk_text)
VALUES (%(chunk_id)s, %(review_id)s, %(chunk_no)s, %(char_start)s, %(char_end)s, %(chunk_text)s)
ON CONFLICT DO NOTHING
"""

INSERT_ASPECT = """
INSERT INTO review_aspects (review_id, aspect, sentiment, evidence_quote, label_version)
VALUES (%(review_id)s, %(aspect)s, %(sentiment)s, %(evidence_quote)s, %(label_version)s)
ON CONFLICT DO NOTHING
"""

MARK_LABELED = """
UPDATE reviews SET label_status = 'labeled', label_version = %(label_version)s
WHERE review_id = %(review_id)s
"""


def review_row(record: dict) -> dict:
    return {**record, "body": record["text"], "rating": int(record["rating"])}


def chunk_rows(review_id: str, body: str, ranges: list[list[int]]) -> list[dict]:
    return [
        {
            "chunk_id": f"{review_id}:{chunk_no}",
            "review_id": review_id,
            "chunk_no": chunk_no,
            "char_start": start,
            "char_end": end,
            "chunk_text": body[start:end],
        }
        for chunk_no, (start, end) in enumerate(ranges, start=1)
    ]


def upsert_product(conn: psycopg.Connection, product: dict) -> int:
    return conn.execute(UPSERT_PRODUCT, product).rowcount


def insert_review(conn: psycopg.Connection, row: dict) -> int:
    return conn.execute(INSERT_REVIEW, row).rowcount


def insert_chunks(conn: psycopg.Connection, review_id: str, body: str, ranges: list[list[int]]) -> int:
    return sum(conn.execute(INSERT_CHUNK, row).rowcount for row in chunk_rows(review_id, body, ranges))


def insert_aspect(conn: psycopg.Connection, label: dict) -> int:
    inserted = conn.execute(INSERT_ASPECT, label).rowcount
    conn.execute(MARK_LABELED, label)
    return inserted