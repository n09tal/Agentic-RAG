"""Extract the demo products and all of their reviews into a local staging area.

Usage:
    uv run python -m ingest.extract_reviews --data-dir C:/Agentic-RAG-data
"""

import argparse
import gzip
import hashlib
import json
from collections import Counter
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from ingest.demo_products import DEMO_PRODUCTS

META_FILE = "meta_Electronics.jsonl.gz"
REVIEWS_FILE = "Electronics.jsonl.gz"
PRODUCT_FIELDS = [
    "parent_asin", "title", "store", "main_category", "categories",
    "details", "price", "average_rating", "rating_number",
]


def make_review_id(user_id: str, asin: str, timestamp: int) -> str:
    key = f"{user_id}|{asin}|{timestamp}"
    return "r_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def iter_matching_lines(path: Path, needles: set[str]) -> Iterator[tuple[int, dict]]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if any(needle in line for needle in needles):
                yield line_no, json.loads(line)


def extract_products(meta_path: Path, parent_asins: set[str]) -> list[dict]:
    products = []
    for _, item in iter_matching_lines(meta_path, parent_asins):
        if item["parent_asin"] in parent_asins:
            products.append({field: item.get(field) for field in PRODUCT_FIELDS})
    return products


def to_staging_record(review: dict, source_line: int) -> dict:
    return {
        "review_id": make_review_id(review["user_id"], review["asin"], review["timestamp"]),
        "parent_asin": review["parent_asin"],
        "asin": review["asin"],
        "user_id": review["user_id"],
        "rating": review["rating"],
        "title": review["title"],
        "text": review["text"],
        "timestamp": review["timestamp"],
        "reviewed_at": datetime.fromtimestamp(review["timestamp"] / 1000, tz=timezone.utc).isoformat(),
        "helpful_vote": review["helpful_vote"],
        "verified_purchase": review["verified_purchase"],
        "source_file": REVIEWS_FILE,
        "source_line": source_line,
    }


def extract_reviews(reviews_path: Path, parent_asins: set[str]) -> tuple[list[dict], Counter]:
    records: dict[str, dict] = {}
    issues = Counter()
    for line_no, review in iter_matching_lines(reviews_path, parent_asins):
        if review["parent_asin"] not in parent_asins:
            continue
        record = to_staging_record(review, line_no)
        existing = records.get(record["review_id"])
        if existing is None:
            records[record["review_id"]] = record
        elif (existing["rating"], existing["title"], existing["text"]) == (
            record["rating"], record["title"], record["text"]
        ):
            issues["exact_duplicate"] += 1
        else:
            issues["conflict"] += 1
            print(f"  conflict: {record['review_id']} at lines {existing['source_line']} and {line_no}")
    return list(records.values()), issues


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    parent_asins = set(DEMO_PRODUCTS)
    staging = args.data_dir / "staging"

    products = extract_products(args.data_dir / META_FILE, parent_asins)
    write_jsonl(staging / "products.jsonl", products)
    print(f"Products: {len(products)}")

    reviews, issues = extract_reviews(args.data_dir / REVIEWS_FILE, parent_asins)
    write_jsonl(staging / "reviews_raw.jsonl", reviews)
    per_product = Counter(review["parent_asin"] for review in reviews)
    for asin, name in DEMO_PRODUCTS.items():
        print(f"  {name} ({asin}): {per_product[asin]} reviews")
    print(f"Reviews: {len(reviews)}  exact duplicates skipped: {issues['exact_duplicate']}"
          f"  conflicts: {issues['conflict']}")
    print(f"Wrote {staging / 'products.jsonl'} and {staging / 'reviews_raw.jsonl'}")


if __name__ == "__main__":
    main()