import gzip
import json

from ingest.approve_reviews import make_decision
from ingest.build_snapshot import build_manifest, snapshot_records
from ingest.verify_snapshot import count_manifest_mismatches, count_source_mismatches, count_unapproved


def review(review_id, parent_asin="P1", text="Great sound.", source_line=1):
    return {
        "review_id": review_id, "parent_asin": parent_asin, "asin": parent_asin,
        "user_id": "U1", "rating": 5.0, "title": "Great", "text": text,
        "timestamp": 1, "source_line": source_line,
    }


def test_snapshot_keeps_only_approved_reviews_and_marks_them():
    reviews = [review("r_1"), review("r_2"), review("r_3")]
    decisions = {
        "r_1": make_decision("r_1", "approved", None),
        "r_2": make_decision("r_2", "rejected", "non_english"),
    }

    records = snapshot_records(reviews, decisions, "demo-test")

    assert [r["review_id"] for r in records] == ["r_1"]
    assert records[0]["language_approved"] is True
    assert records[0]["review_language"] == "en"
    assert records[0]["snapshot_id"] == "demo-test"


def test_manifest_counts_every_outcome():
    reviews = [review("r_1"), review("r_2", parent_asin="P2"), review("r_3"), review("r_4")]
    decisions = {
        "r_1": make_decision("r_1", "approved", None),
        "r_2": make_decision("r_2", "approved", None),
        "r_3": make_decision("r_3", "rejected", "unreadable"),
    }
    records = snapshot_records(reviews, decisions, "demo-test")

    manifest = build_manifest("demo-test", reviews, decisions, records, "abc")

    assert manifest["counts"]["approved"] == 2
    assert manifest["counts"]["rejected_unreadable"] == 1
    assert manifest["counts"]["undecided"] == 1
    assert manifest["counts"]["approved_per_product"] == {"P1": 1, "P2": 1}
    assert manifest["approved_review_ids"] == ["r_1", "r_2"]
    assert manifest["rejected"] == [{"review_id": "r_3", "reason": "unreadable"}]


def test_verify_detects_manifest_and_approval_problems():
    records = snapshot_records([review("r_1"), review("r_2")], {
        "r_1": make_decision("r_1", "approved", None),
        "r_2": make_decision("r_2", "approved", None),
    }, "demo-test")
    records[1]["language_approved"] = False

    assert count_manifest_mismatches({"approved_review_ids": ["r_1", "r_9"]}, records) == 2
    assert count_unapproved(records, "demo-test") == 1


def test_verify_detects_text_that_differs_from_source(tmp_path):
    source = tmp_path / "reviews.jsonl.gz"
    with gzip.open(source, "wt", encoding="utf-8") as f:
        f.write(json.dumps(review("r_1", source_line=1)) + "\n")
        f.write(json.dumps(review("r_2", source_line=2)) + "\n")
    records = [review("r_1", source_line=1), review("r_2", text="Great sound!", source_line=2)]

    assert count_source_mismatches(source, records) == 1