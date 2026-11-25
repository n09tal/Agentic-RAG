"""Freeze approved reviews into a versioned demo snapshot.

Writes the manifest (committed) to snapshots/<snapshot-id>.json and the approved
review records (local only) to <data-dir>/staging/snapshot_<snapshot-id>.jsonl.

Usage:
    uv run python -m ingest.build_snapshot --data-dir C:/Agentic-RAG-data --snapshot-id demo-v1
"""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ingest.approve_reviews import latest_decisions, read_jsonl
from ingest.demo_products import DEMO_PRODUCTS
from ingest.extract_reviews import REVIEWS_FILE, write_jsonl
from ingest.screen_language import MIN_ENGLISH_SCORE, MODEL_FILE

SNAPSHOT_DIR = Path("snapshots")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_records(reviews: list[dict], decisions: dict[str, dict], snapshot_id: str) -> list[dict]:
    return [
        {**review, "review_language": "en", "language_approved": True, "snapshot_id": snapshot_id}
        for review in reviews
        if decisions.get(review["review_id"], {}).get("decision") == "approved"
    ]


def build_manifest(
    snapshot_id: str,
    reviews: list[dict],
    decisions: dict[str, dict],
    records: list[dict],
    records_sha256: str,
) -> dict:
    outcomes = Counter(decision["reason"] or decision["decision"] for decision in decisions.values())
    rejected = [
        {"review_id": review_id, "reason": decision["reason"]}
        for review_id, decision in sorted(decisions.items())
        if decision["decision"] == "rejected"
    ]
    return {
        "snapshot_id": snapshot_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_file": REVIEWS_FILE,
        "products": DEMO_PRODUCTS,
        "language_screening": {"model": MODEL_FILE, "min_english_score": MIN_ENGLISH_SCORE},
        "counts": {
            "staged": len(reviews),
            "approved": len(records),
            "rejected_non_english": outcomes["non_english"],
            "rejected_unreadable": outcomes["unreadable"],
            "undecided": len(reviews) - len(decisions),
            "approved_per_product": dict(Counter(record["parent_asin"] for record in records)),
        },
        "records_sha256": records_sha256,
        "approved_review_ids": sorted(record["review_id"] for record in records),
        "rejected": rejected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    args = parser.parse_args()
    staging = args.data_dir / "staging"
    manifest_path = SNAPSHOT_DIR / f"{args.snapshot_id}.json"
    if manifest_path.exists():
        raise SystemExit(f"{manifest_path} already exists. Snapshots are immutable; use a new id.")

    reviews = read_jsonl(staging / "reviews_raw.jsonl")
    decisions = latest_decisions(read_jsonl(staging / "approval_decisions.jsonl"))
    records = snapshot_records(reviews, decisions, args.snapshot_id)

    records_path = staging / f"snapshot_{args.snapshot_id}.jsonl"
    write_jsonl(records_path, records)
    manifest = build_manifest(args.snapshot_id, reviews, decisions, records, file_sha256(records_path))

    SNAPSHOT_DIR.mkdir(exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"], indent=2))
    print(f"Wrote {manifest_path} and {records_path}")


if __name__ == "__main__":
    main()