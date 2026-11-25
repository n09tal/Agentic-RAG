"""Approve or reject staged reviews one by one for the public demo snapshot.

Decisions are appended to staging/approval_decisions.jsonl, so you can quit at any
time and continue later. The latest decision for a review wins.

Usage:
    uv run python -m ingest.approve_reviews --data-dir C:/Agentic-RAG-data
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ingest.demo_products import DEMO_PRODUCTS
from ingest.screen_language import HTML_BREAK

KEYS = {
    "a": ("approved", None),
    "n": ("rejected", "non_english"),
    "e": ("rejected", "unreadable"),
}
HELP = "[a] approve  [n] reject: not English  [e] reject: empty/unreadable  [s] skip  [u] undo  [q] quit"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def latest_decisions(records: list[dict]) -> dict[str, dict]:
    decisions = {}
    for record in records:
        if record["decision"] == "undecided":
            decisions.pop(record["review_id"], None)
        else:
            decisions[record["review_id"]] = record
    return decisions


def review_queue(reviews: list[dict], screening: dict[str, dict], decided: set[str]) -> list[dict]:
    pending = [review for review in reviews if review["review_id"] not in decided]
    return sorted(pending, key=lambda review: screening[review["review_id"]]["status"] != "needs_review")


def make_decision(review_id: str, decision: str, reason: str | None) -> dict:
    return {
        "review_id": review_id,
        "decision": decision,
        "reason": reason,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }


def show(review: dict, screen: dict, decided: int, total: int) -> None:
    print("\n" + "=" * 80)
    print(f"[{decided}/{total} decided]  {DEMO_PRODUCTS[review['parent_asin']]}"
          f"  rating {review['rating']}  {review['review_id']}")
    if screen["status"] == "needs_review":
        print(f"NEEDS REVIEW: {', '.join(screen['reasons'])}"
              f"  (text {screen['text_lang']} {screen['text_score']},"
              f" title {screen['title_lang']} {screen['title_score']})")
    text = HTML_BREAK.sub("\n       ", review["text"])
    print(f"\nTITLE: {review['title']}")
    print(f"TEXT:  {text}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    staging = args.data_dir / "staging"
    decisions_path = staging / "approval_decisions.jsonl"

    reviews = read_jsonl(staging / "reviews_raw.jsonl")
    screening = {screen["review_id"]: screen for screen in read_jsonl(staging / "language_screening.jsonl")}
    decisions = latest_decisions(read_jsonl(decisions_path))
    queue = review_queue(reviews, screening, set(decisions))
    print(f"{len(decisions)} of {len(reviews)} reviews already decided, {len(queue)} to go.")
    print(HELP)

    history: list[tuple[int, str]] = []
    i = 0
    with decisions_path.open("a", encoding="utf-8") as out:
        while i < len(queue):
            review = queue[i]
            show(review, screening[review["review_id"]], len(decisions), len(reviews))
            key = input("> ").strip().lower()

            if key == "q":
                break
            if key == "s":
                i += 1
                continue
            if key == "u":
                if not history:
                    print("Nothing to undo.")
                    continue
                i, review_id = history.pop()
                record = make_decision(review_id, "undecided", None)
                decisions.pop(review_id)
            elif key in KEYS:
                record = make_decision(review["review_id"], *KEYS[key])
                decisions[review["review_id"]] = record
                history.append((i, review["review_id"]))
                i += 1
            else:
                print(HELP)
                continue

            out.write(json.dumps(record) + "\n")
            out.flush()

    outcomes = Counter(d["reason"] or d["decision"] for d in decisions.values())
    print(f"\nDecided {len(decisions)} of {len(reviews)}: {dict(outcomes)}")
    print(f"Decisions are saved in {decisions_path}")


if __name__ == "__main__":
    main()