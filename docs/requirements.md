# Demo Questions & Answer Shape

## 1. Goal
Build an AI agent that answers questions about headphones using **real Amazon reviews**
(Amazon Reviews 2023, Electronics category). Every number must be recomputable from the database, and every quote must link back to the original review.

## 2. Scope
- **Category:** Headphones
- **Products:** two headphones that actually exist in the snapshot — *Product A / Product B (placeholder)*
- **Aspects:** battery life, noise cancellation, comfort/fit
- **Reviews:** only human-approved reviews in a frozen, versioned snapshot

## 3. Three Question Types

| Type | question | What the system queries | The answer include |
|---|---|---|---|
| 1. Find quotes | "Do reviewers say Product A feels too tight after a while?" | Semantic search over review chunks of Product A | 3–5 verbatim excerpts, each with its review_id and a "View original review" link |
| 2. Compute a rate | "What percentage of Product A reviews complain about battery life?" | SQL count over labeled reviews, deduplicated by review_id | Numerator, denominator, percentage, labeling coverage |
| 3. Compare + cite | "Which of these two headphones gets more complaints about battery life? Show me one original review for each." | Rate for A and B (SQL) + one supporting search per product | Both rates with their denominators, which one is higher, one excerpt per product |

**Follow-up:** "What about noise cancellation?" — keep the same two products, switch the aspect.

## 4. Answer Sketch (for Type 3)

    Product A (parent_asin: <TBD>): 8 of 100 labeled reviews complain about battery life (8.0%).
    Product B (parent_asin: <TBD>): 3 of 120 labeled reviews complain about battery life (2.5%).
    → Product A gets proportionally more battery-life complaints.

    Example reviews
    - Product A · ★2 · <date>: "<verbatim excerpt>"   [View original review]
    - Product B · ★3 · <date>: "<verbatim excerpt>"   [View original review]

    Based on 220 reviews in this dataset. (Labeled: 220 / 220)

*Numbers above are illustrative only. Real excerpts will be copied verbatim from the source in next Step*

## 5. Metric Definitions
- **Complaint rate (primary)** = reviews with a negative label on the aspect ÷ labeled reviews of that product
- **Complaint rate among mentions (secondary)** = reviews with a negative label on the aspect ÷ reviews that mention the aspect
- Counts are per **review**, never per chunk: one review split into 3 chunks counts once.
- Rates are computed only from SQL counts, never estimated from search results.
- The rule for mixed sentiment (e.g. "battery is great but charging case is weak") will be fixed in Step 08.

## 6. When to Answer "Insufficient Data"
- The denominator is 0 (no labeled reviews for that product/aspect)
- Labeling coverage is partial → report the rate "within labeled reviews" and show the coverage
- The product cannot be found → ask the user to rephrase
- The model name is ambiguous → show candidates and let the user choose (never guess a model)
- Semantic search returns no relevant review → say so instead of inventing a quote
- The question is about an aspect outside v1 (e.g. price history trends) → state it is out of scope

## 7. Acceptance Checklist
- [ ] For each question type, I can explain what data is queried and what the answer contains
- [ ] Every number in an answer shows its numerator and denominator
- [ ] Every quote has a review_id and a "View original review" entry
- [ ] The "insufficient data" cases are listed