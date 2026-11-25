"""Screen staged reviews by language before human approval.

Usage:
    uv run python -m ingest.screen_language --data-dir C:/Agentic-RAG-data
"""

import argparse
import json
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import fasttext

from ingest.extract_reviews import write_jsonl

MODEL_FILE = "lid.176.bin"
MIN_TEXT_LETTERS = 20
MIN_TITLE_LETTERS = 10
MIN_ENGLISH_SCORE = 0.80
MIN_FOREIGN_SCORE = 0.80

HTML_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

Predictor = Callable[[str], tuple[str, float]]


def count_letters(text: str) -> int:
    return sum(char.isalpha() for char in text)


def normalize_for_detection(text: str) -> str:
    return HTML_BREAK.sub(" ", text).replace("\n", " ").strip()


def is_confident_foreign(lang: str, score: float) -> bool:
    return lang != "en" and score >= MIN_FOREIGN_SCORE


def screen_review(review: dict, predict: Predictor) -> dict:
    reasons = []
    text = normalize_for_detection(review["text"])
    title = normalize_for_detection(review["title"])

    text_lang, text_score = predict(text) if text else ("", 0.0)
    if not text:
        reasons.append("empty_text")
    elif count_letters(text) < MIN_TEXT_LETTERS:
        reasons.append("short_text")
    else:
        if text_lang != "en" or text_score < MIN_ENGLISH_SCORE:
            reasons.append("text_not_confident_english")
        sentences = [s for s in SENTENCE_END.split(text) if count_letters(s) >= MIN_TEXT_LETTERS]
        if any(is_confident_foreign(*predict(sentence)) for sentence in sentences):
            reasons.append("foreign_sentence")

    title_lang, title_score = predict(title) if title else ("", 0.0)
    if count_letters(title) >= MIN_TITLE_LETTERS and is_confident_foreign(title_lang, title_score):
        reasons.append("title_not_english")

    return {
        "review_id": review["review_id"],
        "status": "needs_review" if reasons else "english_candidate",
        "reasons": reasons,
        "text_lang": text_lang,
        "text_score": round(text_score, 4),
        "title_lang": title_lang,
        "title_score": round(title_score, 4),
    }


def load_predictor(model_path: Path) -> Predictor:
    model = fasttext.load_model(str(model_path))

    def predict(text: str) -> tuple[str, float]:
        labels, scores = model.predict(text, k=1)
        return labels[0].removeprefix("__label__"), float(scores[0])

    return predict


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    staging = args.data_dir / "staging"

    predict = load_predictor(args.data_dir / "models" / MODEL_FILE)
    with (staging / "reviews_raw.jsonl").open(encoding="utf-8") as f:
        reviews = [json.loads(line) for line in f]

    results = [screen_review(review, predict) for review in reviews]
    write_jsonl(staging / "language_screening.jsonl", results)

    statuses = Counter(result["status"] for result in results)
    reasons = Counter(reason for result in results for reason in result["reasons"])
    print(f"Screened {len(results)} reviews")
    print(f"  english_candidate: {statuses['english_candidate']}")
    print(f"  needs_review:      {statuses['needs_review']}")
    for reason, count in reasons.most_common():
        print(f"    {reason}: {count}")
    print(f"Wrote {staging / 'language_screening.jsonl'}")


if __name__ == "__main__":
    main()