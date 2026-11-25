# Data Source

## Dataset
- **Amazon Reviews 2023** (McAuley Lab, UC San Diego): https://amazon-reviews-2023.github.io/
- Category: Electronics
- Citation: Hou, Y., Li, J., He, Z., Yan, A., Chen, X., & McAuley, J. (2024).
  *Bridging Language and Items for Retrieval and Recommendation.* arXiv:2403.03952.

## Files (stored locally, never committed)
| File | Content |
|---|---|
| `meta_Electronics.jsonl.gz` | Product metadata: title, store, details (model number), categories, `parent_asin` |
| `Electronics.jsonl.gz` | Reviews: rating, title, text, timestamp, `asin`, `parent_asin`, `user_id` |

Products and reviews are joined on `parent_asin`. One parent groups variants such as colors;
each review keeps its specific `asin`.

## Candidate selection
Script: `ingest/find_headphone_candidates.py`
1. Keep products whose `categories` include **"Headphones & Earbuds"** (excludes cases, ear pads, adapters).
2. Count reviews per `parent_asin` in the review file.
3. Keep products with at least 100 reviews.

Result: 56,048 headphone products, 3,123,938 reviews of headphone products,
4,468 candidates with >= 100 reviews.

Shortlist filters applied to the candidates: subcategory "Over-Ear Headphones", title mentions noise cancelling and wireless/Bluetooth, a model number is present, 300-1,000 reviews (43 products).

## Demo products
| | Product A | Product B |
|---|---|---|
| parent_asin | `B0C5ZC7FWR` | `B0B95V4ZBW` |
| Title | Sony WH-1000XM5 Wireless Industry Leading Headphones with Auto Noise Canceling Optimizer, Crystal Clear Hands-Free Calling, and Alexa Voice Control, Midnight Blue WH1000XM5 | Sennheiser Momentum 4 Wireless Headphones - Bluetooth Headset for Crystal-Clear Calls with Adaptive Noise Cancellation, 60h Battery Life, Customizable Sound - White |
| Brand / model | Sony / WH-1000XM5 (model no. `WH1000XM5/L`) | Sennheiser / Momentum 4 Wireless (model no. `509267`) |
| Subcategory | Over-Ear Headphones | Over-Ear Headphones |
| Variants (`asin`) in reviews | 3 | 2 |
| Review lines in dataset (before de-duplication) | 825 | 333 |
| Average rating / rating count on Amazon | 4.5 / 5,658 | 4.1 / 2,091 |
| Recorded price | $398.00 | $299.95 |

**Why these two**
- **Comparable:** both are flagship wireless over-ear noise-cancelling headphones released in 2022, from different brands, at a similar price. A head-to-head comparison is meaningful.
- **One listing covers the model:** many models are split across several listings in the dataset (e.g. Bose 700: 730 vs 2,991 reviews; Bose QC35 II: 5 listings). For these two, the chosen listing holds nearly all of the model's reviews (WH-1000XM5: 825 of 936; Momentum 4: 333 of 344), so every review of the listing can be used without sampling.
- **Right size:** 1,143 unique reviews in total (1,158 lines before de-duplication), small enough to approve review by review and large enough for meaningful rates.
- **All demo aspects are discussed** (keyword check used only for selection; real labels come later): battery/charging 144 vs 131, noise cancelling 449 vs 154, comfort/fit 307 vs 132.
- **Ratings differ:** 1-2 star reviews are 19% (Sony) vs 26% (Sennheiser), so comparisons are likely to show real differences.
- **Disambiguation test case:** the dataset also contains Sony WF-1000XM5 earbuds, so a query like "Sony 1000XM5" should trigger a model clarification instead of a guess.

## Extraction (staging)
Script: `ingest/extract_reviews.py` writes `staging/products.jsonl` and `staging/reviews_raw.jsonl` to the local data directory (never committed).

- **review_id** = `r_` + first 16 hex characters of SHA-256(`user_id|asin|timestamp`).
  The same source record always gets the same ID, so re-running the import never creates new IDs.
- **Source locator:** each review keeps `source_file` and `source_line` (1-based line number in the decompressed file), so any excerpt can be checked against the original record.
- Title and text are copied verbatim (no cleaning or spelling fixes).
- **Duplicates:** the source file repeats 13 reviews as 15 byte-identical extra lines for these two products. They are skipped and counted. Records with the same ID but different content would be reported as conflicts; none were found.

| | Sony WH-1000XM5 | Sennheiser Momentum 4 |
|---|---|---|
| Review lines in source | 825 | 333 |
| Unique reviews after de-duplication | 814 | 329 |

## Language screening
Script: `ingest/screen_language.py` writes `staging/language_screening.jsonl` (local, never committed). It only sorts reviews for human review; every review in the public snapshot is still approved by a person.

- **Model:** fastText language identification `lid.176.bin`
  (https://fasttext.cc/docs/en/language-identification.html, CC BY-SA 3.0), run with the
  `fasttext-predict` package and stored in `models/` in the local data directory.
- Before detection, `<br />` tags and newlines are replaced by spaces. The stored text is unchanged.

| Rule | Reason code |
|---|---|
| Text is empty | `empty_text` |
| Text has fewer than 20 letters | `short_text` |
| Text is not detected as English with score >= 0.80 | `text_not_confident_english` |
| A sentence with >= 20 letters is detected as another language with score >= 0.80 | `foreign_sentence` |
| Title has >= 10 letters and is detected as another language with score >= 0.80 | `title_not_english` |

A review with any reason is `needs_review`; otherwise it is an `english_candidate`.

**Threshold calibration:** with the 0.95 starting point from the project plan, 275 of 1,143 reviews would need review, and spot checks showed they were almost all plain English. At 0.80, all 18 Spanish reviews are still caught, and spot-checked reviews scoring 0.80-0.90 were English. Short titles are unreliable (e.g. "Love love love!" was detected as Spanish), so titles are flagged only when confidently foreign.

| Status / reason | Reviews |
|---|---|
| english_candidate | 1,078 |
| needs_review | 65 |
| - text_not_confident_english | 32 |
| - short_text | 30 |
| - foreign_sentence | 18 |
| - title_not_english | 14 |
| - empty_text | 1 |

A review can have more than one reason.

## Human approval
Tool: `ingest/approve_reviews.py` shows every staged review (those flagged by language screening first) and records one decision per review in `staging/approval_decisions.jsonl` (local, never committed). The file is append-only: the latest decision for a review wins, and undo is recorded as a new line.

Approval criteria:
- **Approve** when both the title and the text are English and readable. Brand names, model numbers, typos and very short English texts (e.g. "Love them!") are fine; text is never edited.
- **Reject: `non_english`** when any part of the title or text is in another language, including mixed-language reviews.
- **Reject: `unreadable`** when the text is empty or has no readable words (only symbols, emoji or numbers).
- **Skip** when unsure; skipped reviews stay undecided and are excluded from the snapshot.

Results: 1,119 approved, 21 rejected as `non_english` (all Spanish), 3 rejected as `unreadable` (empty text, emoji only, numbers only), 0 undecided. Every review was decided against the criteria above

## Demo snapshot `demo-v1`
- Manifest (committed): [`snapshots/demo-v1.json`](../snapshots/demo-v1.json). It lists every approved `review_id`, every rejected `review_id` with its reason, the counts, the language-screening settings, and the SHA-256 of the local snapshot file. It contains no review text.
- Records (local only): `staging/snapshot_demo-v1.jsonl`, approved reviews marked with
  `review_language="en"`, `language_approved=true` and `snapshot_id="demo-v1"`.
- Snapshots are immutable: `ingest/build_snapshot.py` refuses to overwrite an existing id; changes go into a new id such as `demo-v2`.
- Every later step (database import, embeddings, tools, evaluation) reads only this snapshot.

| | Sony WH-1000XM5 | Sennheiser Momentum 4 | Total |
|---|---|---|---|
| Approved reviews | 797 | 322 | 1,119 |

**Verification** (`ingest/verify_snapshot.py`, must all be 0 before the snapshot is used):

| Check | Result |
|---|---|
| Reviews outside the manifest (or listed but missing) | 0 |
| Reviews not marked as approved English | 0 |
| Reviews whose title, text or metadata differ from the source line | 0 |
| Local file checksum matches the manifest | yes |

## Scope and notes
- Statistics cover **the chosen listing only**. Smaller listings of the same models are excluded (WH-1000XM5: 8 listings, 111 reviews; Momentum 4: 1 listing, 11 reviews).
- `rating_number` (metadata) is the rating count shown on Amazon; `review_count` is the number of reviews actually in this dataset. All statistics in this project use the dataset count.
- Results describe this dataset snapshot only, not Amazon as a whole.