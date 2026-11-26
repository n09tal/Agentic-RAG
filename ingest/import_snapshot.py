"""Import a verified demo snapshot into the database.

Usage:
    uv run python -m ingest.import_snapshot --data-dir C:/Agentic-RAG-data --snapshot-id demo-v1
"""

import argparse
import json
from pathlib import Path

import psycopg

from backend.config import get_settings
from ingest.approve_reviews import read_jsonl
from ingest.build_snapshot import SNAPSHOT_DIR, file_sha256
from ingest.db_writer import insert_review, review_row, upsert_product
from ingest.find_headphone_candidates import extract_model

STORED_REVIEWS = """
SELECT review_id, parent_asin, rating, title, body
FROM reviews
WHERE review_id = ANY(%s)
"""
REVIEWS_PER_PRODUCT = """
SELECT parent_asin, count(*)
FROM reviews
WHERE snapshot_id = %s
GROUP BY parent_asin
"""


class SnapshotImportError(RuntimeError):
    pass


def product_row(meta: dict) -> dict:
    details = meta.get("details") or {}
    categories = meta.get("categories") or []
    return {
        "parent_asin": meta["parent_asin"],
        "title": meta["title"],
        "brand": details.get("Brand") or meta.get("store"),
        "model_number": extract_model(details) or None,
        "category": categories[-1] if categories else None,
        "recorded_price": meta.get("price"),
    }


def read_snapshot(data_dir: Path, snapshot_id: str, snapshot_dir: Path = SNAPSHOT_DIR) -> tuple[dict, list[dict]]:
    manifest = json.loads((snapshot_dir / f"{snapshot_id}.json").read_text(encoding="utf-8"))
    records_path = data_dir / "staging" / f"snapshot_{snapshot_id}.jsonl"
    if file_sha256(records_path) != manifest["records_sha256"]:
        raise SnapshotImportError(
            f"{records_path.name} does not match the manifest checksum. Run ingest.verify_snapshot first."
        )
    return manifest, read_jsonl(records_path)


def import_snapshot(conn: psycopg.Connection, manifest: dict, records: list[dict], products: list[dict]) -> dict:
    wanted = set(manifest["products"])
    product_rows = [product_row(product) for product in products if product["parent_asin"] in wanted]
    missing = wanted - {product["parent_asin"] for product in product_rows}
    if missing:
        raise SnapshotImportError(f"Product metadata missing for {sorted(missing)}")
    rows = [review_row(record) for record in records]

    with conn.transaction():
        for product in product_rows:
            upsert_product(conn, product)
        inserted = sum(insert_review(conn, row) for row in rows)

        stored = {
            review_id: values
            for review_id, *values in conn.execute(STORED_REVIEWS, ([row["review_id"] for row in rows],))
        }
        conflicts = [
            row["review_id"] for row in rows
            if stored.get(row["review_id"]) != [row["parent_asin"], row["rating"], row["title"], row["body"]]
        ]
        if conflicts:
            raise SnapshotImportError(
                f"{len(conflicts)} stored review(s) differ from the snapshot, e.g. {conflicts[0]}. Nothing was imported."
            )

        per_product = dict(conn.execute(REVIEWS_PER_PRODUCT, (manifest["snapshot_id"],)).fetchall())
        if per_product != manifest["counts"]["approved_per_product"]:
            raise SnapshotImportError(
                f"Reviews per product {per_product} do not match the manifest "
                f"{manifest['counts']['approved_per_product']}. Nothing was imported."
            )

    return {"products": len(product_rows), "inserted": inserted, "skipped": len(rows) - inserted,
            "per_product": per_product}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    args = parser.parse_args()

    manifest, records = read_snapshot(args.data_dir, args.snapshot_id)
    products = read_jsonl(args.data_dir / "staging" / "products.jsonl")
    with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
        result = import_snapshot(conn, manifest, records, products)

    print(f"Snapshot {args.snapshot_id}: {result['products']} products, "
          f"{result['inserted']} reviews inserted, {result['skipped']} already present")
    for asin, count in sorted(result["per_product"].items()):
        print(f"  {manifest['products'][asin]} ({asin}): {count} reviews in the database")


if __name__ == "__main__":
    main()