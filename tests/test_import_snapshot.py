import json

import psycopg
import pytest

from db.migrate import migrate
from ingest.build_snapshot import file_sha256
from ingest.extract_reviews import write_jsonl
from ingest.import_snapshot import SnapshotImportError, import_snapshot, product_row, read_snapshot

PRODUCTS = [
    {"parent_asin": "P1", "title": "Headphones One", "store": "Acme Store",
     "details": {"Item model number": "A-1"}, "categories": ["Electronics", "Over-Ear Headphones"], "price": 99.5},
    {"parent_asin": "P2", "title": "Headphones Two", "store": "Beta Store",
     "details": {"Brand": "Beta"}, "categories": [], "price": None},
]


def record(review_id, parent_asin, line, text="Great sound."):
    return {
        "review_id": review_id, "parent_asin": parent_asin, "asin": parent_asin, "rating": 5.0,
        "title": "Great", "text": text, "reviewed_at": "2023-01-01T00:00:00+00:00", "helpful_vote": 0,
        "verified_purchase": True, "review_language": "en", "language_approved": True,
        "snapshot_id": "demo-test", "source_file": "reviews.jsonl.gz", "source_line": line,
    }


RECORDS = [record("r_1", "P1", 1), record("r_2", "P1", 2), record("r_3", "P2", 3)]
MANIFEST = {
    "snapshot_id": "demo-test",
    "products": {"P1": "One", "P2": "Two"},
    "counts": {"approved_per_product": {"P1": 2, "P2": 1}},
}


@pytest.fixture
def db(fresh_database_url):
    migrate(fresh_database_url)
    with psycopg.connect(fresh_database_url, autocommit=True) as conn:
        yield conn


def test_product_row_maps_metadata():
    assert product_row(PRODUCTS[0]) == {
        "parent_asin": "P1", "title": "Headphones One", "brand": "Acme Store",
        "model_number": "A-1", "category": "Over-Ear Headphones", "recorded_price": 99.5,
    }
    assert product_row(PRODUCTS[1])["brand"] == "Beta"
    assert product_row(PRODUCTS[1])["category"] is None


def test_import_loads_everything_and_a_rerun_inserts_nothing(db):
    first = import_snapshot(db, MANIFEST, RECORDS, PRODUCTS)
    second = import_snapshot(db, MANIFEST, RECORDS, PRODUCTS)

    assert (first["inserted"], first["skipped"]) == (3, 0)
    assert (second["inserted"], second["skipped"]) == (0, 3)
    assert second["per_product"] == {"P1": 2, "P2": 1}
    assert db.execute("SELECT count(*) FROM products").fetchone()[0] == 2


def test_changed_review_content_is_rejected_and_nothing_changes(db):
    import_snapshot(db, MANIFEST, RECORDS, PRODUCTS)
    changed = [record("r_1", "P1", 1, text="Edited text."), *RECORDS[1:], record("r_4", "P2", 4)]

    with pytest.raises(SnapshotImportError, match=r"1 stored review\(s\) differ"):
        import_snapshot(db, MANIFEST, changed, PRODUCTS)

    assert db.execute("SELECT body FROM reviews WHERE review_id = 'r_1'").fetchone()[0] == "Great sound."
    assert db.execute("SELECT count(*) FROM reviews").fetchone()[0] == 3


def test_count_mismatch_with_the_manifest_is_rejected(db):
    manifest = {**MANIFEST, "counts": {"approved_per_product": {"P1": 2, "P2": 2}}}

    with pytest.raises(SnapshotImportError, match="do not match the manifest"):
        import_snapshot(db, manifest, RECORDS, PRODUCTS)

    assert db.execute("SELECT count(*) FROM reviews").fetchone()[0] == 0


def test_read_snapshot_rejects_a_modified_records_file(tmp_path):
    records_path = tmp_path / "staging" / "snapshot_demo-test.jsonl"
    write_jsonl(records_path, RECORDS)
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    manifest = {**MANIFEST, "records_sha256": file_sha256(records_path)}
    (snapshot_dir / "demo-test.json").write_text(json.dumps(manifest), encoding="utf-8")

    assert len(read_snapshot(tmp_path, "demo-test", snapshot_dir)[1]) == 3

    with records_path.open("a", encoding="utf-8") as f:
        f.write("\n")
    with pytest.raises(SnapshotImportError, match="checksum"):
        read_snapshot(tmp_path, "demo-test", snapshot_dir)