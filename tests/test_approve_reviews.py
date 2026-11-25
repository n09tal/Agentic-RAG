import json
import sys

from ingest import approve_reviews
from ingest.approve_reviews import latest_decisions, make_decision, review_queue


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def test_latest_decision_wins_and_undecided_removes_it():
    records = [
        make_decision("r_1", "approved", None),
        make_decision("r_1", "rejected", "non_english"),
        make_decision("r_2", "approved", None),
        make_decision("r_2", "undecided", None),
    ]

    decisions = latest_decisions(records)

    assert list(decisions) == ["r_1"]
    assert decisions["r_1"]["reason"] == "non_english"


def test_queue_puts_needs_review_first_and_skips_decided():
    reviews = [{"review_id": "r_1"}, {"review_id": "r_2"}, {"review_id": "r_3"}]
    screening = {
        "r_1": {"status": "english_candidate"},
        "r_2": {"status": "english_candidate"},
        "r_3": {"status": "needs_review"},
    }

    queue = review_queue(reviews, screening, decided={"r_2"})

    assert [review["review_id"] for review in queue] == ["r_3", "r_1"]


def test_session_saves_decisions_and_supports_undo(tmp_path, monkeypatch):
    staging = tmp_path / "staging"
    staging.mkdir()
    reviews = [
        {"review_id": f"r_{n}", "parent_asin": "B0C5ZC7FWR", "rating": 5.0,
         "title": "Great", "text": "Great sound."}
        for n in (1, 2, 3)
    ]
    write_jsonl(staging / "reviews_raw.jsonl", reviews)
    write_jsonl(staging / "language_screening.jsonl", [
        {"review_id": r["review_id"], "status": "english_candidate", "reasons": [],
         "text_lang": "en", "text_score": 0.99, "title_lang": "en", "title_score": 0.99}
        for r in reviews
    ])
    keys = iter(["a", "n", "u", "e", "s", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(keys))
    monkeypatch.setattr(sys, "argv", ["approve_reviews", "--data-dir", str(tmp_path)])

    approve_reviews.main()

    lines = (staging / "approval_decisions.jsonl").read_text(encoding="utf-8").splitlines()
    decisions = latest_decisions([json.loads(line) for line in lines])
    assert decisions["r_1"]["decision"] == "approved"
    assert decisions["r_2"]["reason"] == "unreadable"
    assert "r_3" not in decisions