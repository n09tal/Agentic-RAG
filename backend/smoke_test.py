"""Call Gemini once for embeddings and once for an answer, using a real snapshot review.

Usage:
    uv run python -m backend.smoke_test --data-dir C:/Agentic-RAG-data --snapshot-id demo-v1
"""

import argparse
import math
import sys
from pathlib import Path

from backend.config import get_settings
from backend.llm import embed_texts, format_document, format_query, generate_text
from ingest.approve_reviews import read_jsonl

QUESTION = "How do reviewers describe the battery life?"
UNRELATED_TEXT = "The pasta was overcooked and the sauce was far too salty."
PROMPT = """Answer the question using only the review below.
Reply with one sentence, then a new line starting with QUOTE: followed by a short phrase
copied exactly from the review that supports your answer.

Question: {question}
Review {review_id}: {text}"""


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def pick_review(records: list[dict]) -> dict:
    return next(r for r in records if "battery" in r["text"].lower() and 200 <= len(r["text"]) <= 600)


def extract_quote(reply: str) -> str:
    for line in reply.splitlines():
        if line.strip().upper().startswith("QUOTE:"):
            return line.split(":", 1)[1].strip().strip('"“”')
    return ""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    args = parser.parse_args()

    settings = get_settings()
    records = read_jsonl(args.data_dir / "staging" / f"snapshot_{args.snapshot_id}.jsonl")
    review = pick_review(records)
    print(f"Review {review['review_id']}: {review['text'][:120]}...")

    question_vec, review_vec, unrelated_vec = embed_texts(settings, [
        format_query(QUESTION),
        format_document(review["text"], review["title"]),
        format_document(UNRELATED_TEXT),
    ])
    print(f"\nEmbeddings: {settings.embedding_model}, {len(question_vec)} dimensions")
    print(f"  similarity(question, review)    = {cosine_similarity(question_vec, review_vec):.3f}")
    print(f"  similarity(question, unrelated) = {cosine_similarity(question_vec, unrelated_vec):.3f}")

    prompt = PROMPT.format(question=QUESTION, review_id=review["review_id"], text=review["text"])
    reply = generate_text(settings, prompt)
    quote = extract_quote(reply)
    print(f"\nGemini ({settings.gemini_model}):\n{reply}")
    print(f"\nQuote found verbatim in the review: {bool(quote) and quote in review['text']}")


if __name__ == "__main__":
    main()