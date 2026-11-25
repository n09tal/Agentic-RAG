"""Check a demo snapshot before it is used anywhere.

Every check must report 0 problems:
1. Reviews in the local snapshot file that are not listed in the manifest, or the reverse.
2. Reviews that are not marked as approved English reviews of this snapshot.
3. Reviews whose title, text or metadata differ from the original source line.
The local snapshot file must also still have the checksum recorded in the manifest.

Usage:
    uv run python -m ingest.verify_snapshot --data-dir C:/Agentic-RAG-data --snapshot-id demo-v1
"""

import argparse
import gzip
import json
from pathlib import Path

from ingest.approve_reviews import read_jsonl
from ingest.build_snapshot import SNAPSHOT_DIR, file_sha256

COMPARED_FIELDS = ["parent_asin", "asin", "user_id", "rating", "title", "text", "timestamp"]


def count_manifest_mismatches(manifest: dict, records: list[dict]) -> int:
    listed = set(manifest["approved_review_ids"])
    present = {record["review_id"] for record in records}
    return len(listed ^ present)


def count_unapproved(records: list[dict], snapshot_id: str) -> int:
    return sum(
        1 for record in records
        if not (record["language_approved"] is True
                and record["review_language"] == "en"
                and record["snapshot_id"] == snapshot_id)
    )


def count_source_mismatches(source_path: Path, records: list[dict]) -> int:
    by_line = {record["source_line"]: record for record in records}
    last_line = max(by_line, default=0)
    matched = 0
    with gzip.open(source_path, "rt", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if line_no > last_line:
                break
            record = by_line.get(line_no)
            if record is None:
                continue
            source = json.loads(line)
            if all(source[field] == record[field] for field in COMPARED_FIELDS):
                matched += 1
    return len(by_line) - matched


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    args = parser.parse_args()

    manifest = json.loads((SNAPSHOT_DIR / f"{args.snapshot_id}.json").read_text(encoding="utf-8"))
    records_path = args.data_dir / "staging" / f"snapshot_{args.snapshot_id}.jsonl"
    records = read_jsonl(records_path)

    checksum_ok = file_sha256(records_path) == manifest["records_sha256"]
    problems = {
        "not in manifest (or missing)": count_manifest_mismatches(manifest, records),
        "not approved English": count_unapproved(records, args.snapshot_id),
        "differs from source": count_source_mismatches(args.data_dir / manifest["source_file"], records),
    }

    print(f"Snapshot {args.snapshot_id}: {len(records)} reviews")
    print(f"  checksum matches manifest: {checksum_ok}")
    for name, count in problems.items():
        print(f"  {name}: {count}")
    if not checksum_ok or any(problems.values()):
        raise SystemExit("Snapshot verification FAILED")
    print("Snapshot verification passed")


if __name__ == "__main__":
    main()