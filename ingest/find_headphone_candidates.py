"""Find headphone products in Amazon Reviews 2023 and count their reviews.

Usage:
    uv run python -m ingest.find_headphone_candidates --data-dir C:/Agentic-RAG-data
"""

import argparse
import csv
import gzip
import json
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

HEADPHONE_CATEGORY = "Headphones & Earbuds"
MIN_REVIEWS = 100


def read_jsonl_gz(path: Path) -> Iterator[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def extract_model(details: dict) -> str:
    return details.get("Item model number") or details.get("Model Name") or ""


def load_headphones(meta_path: Path) -> dict[str, dict]:
    products = {}
    for item in read_jsonl_gz(meta_path):
        categories = item.get("categories") or []
        if HEADPHONE_CATEGORY not in categories:
            continue
        details = item.get("details") or {}
        products[item["parent_asin"]] = {
            "parent_asin": item["parent_asin"],
            "title": item.get("title") or "",
            "brand": details.get("Brand") or item.get("store") or "",
            "model": extract_model(details),
            "subcategory": categories[-1],
            "average_rating": item.get("average_rating"),
            "rating_number": item.get("rating_number"),
            "price": item.get("price"),
        }
    return products


def count_reviews(reviews_path: Path, parent_asins: set[str]) -> Counter:
    counts = Counter()
    for i, review in enumerate(read_jsonl_gz(reviews_path), start=1):
        if review["parent_asin"] in parent_asins:
            counts[review["parent_asin"]] += 1
        if i % 5_000_000 == 0:
            print(f"  scanned {i:,} reviews...", flush=True)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()

    products = load_headphones(args.data_dir / "meta_Electronics.jsonl.gz")
    print(f"Headphone products: {len(products):,}")

    counts = count_reviews(args.data_dir / "Electronics.jsonl.gz", set(products))
    print(f"Reviews of headphone products: {sum(counts.values()):,}")

    rows = [
        {**product, "review_count": counts[asin]}
        for asin, product in products.items()
        if counts[asin] >= MIN_REVIEWS
    ]
    rows.sort(key=lambda row: row["review_count"], reverse=True)

    out_path = args.data_dir / "candidates" / "headphone_candidates.csv"
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows):,} candidates with >= {MIN_REVIEWS} reviews to {out_path}")


if __name__ == "__main__":
    main()