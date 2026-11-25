import gzip
import json

from ingest.extract_reviews import extract_products, extract_reviews, make_review_id


def write_jsonl_gz(path, records):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def review(parent_asin, user_id="U1", timestamp=1, text="Great sound.", rating=5.0):
    return {
        "parent_asin": parent_asin, "asin": parent_asin, "user_id": user_id,
        "timestamp": timestamp, "rating": rating, "title": "Title", "text": text,
        "helpful_vote": 0, "verified_purchase": True, "images": [],
    }


def test_make_review_id_is_stable_and_distinct():
    first = make_review_id("U1", "A1", 1000)
    assert first == make_review_id("U1", "A1", 1000)
    assert first != make_review_id("U2", "A1", 1000)
    assert first.startswith("r_") and len(first) == 18


def test_extract_reviews_keeps_demo_products_and_records_source_line(tmp_path):
    path = tmp_path / "reviews.jsonl.gz"
    write_jsonl_gz(path, [
        review("OTHER"),
        review("P1", user_id="U2"),
        review("OTHER", user_id="U3", text="Better than P1 in every way."),
    ])

    records, issues = extract_reviews(path, {"P1"})

    assert [r["parent_asin"] for r in records] == ["P1"]
    assert records[0]["source_line"] == 2
    assert records[0]["text"] == "Great sound."
    assert issues == {}


def test_extract_reviews_skips_exact_duplicates_and_counts_conflicts(tmp_path):
    path = tmp_path / "reviews.jsonl.gz"
    write_jsonl_gz(path, [
        review("P1"),
        review("P1"),
        review("P1", text="Changed my mind."),
    ])

    records, issues = extract_reviews(path, {"P1"})

    assert len(records) == 1
    assert issues == {"exact_duplicate": 1, "conflict": 1}


def test_extract_products_keeps_selected_fields(tmp_path):
    path = tmp_path / "meta.jsonl.gz"
    write_jsonl_gz(path, [
        {"parent_asin": "P1", "title": "Headphones", "images": ["big.jpg"]},
        {"parent_asin": "P2", "title": "Speaker"},
    ])

    products = extract_products(path, {"P1"})

    assert len(products) == 1
    assert products[0]["title"] == "Headphones"
    assert "images" not in products[0]