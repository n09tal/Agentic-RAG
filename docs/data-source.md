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

Shortlist filters applied to the candidates: subcategory "Over-Ear Headphones", title mentions
noise cancelling and wireless/Bluetooth, a model number is present, 300-1,000 reviews (43 products).

## Demo products
| | Product A | Product B |
|---|---|---|
| parent_asin | `B0C5ZC7FWR` | `B0B95V4ZBW` |
| Title | Sony WH-1000XM5 Wireless Industry Leading Headphones with Auto Noise Canceling Optimizer, Crystal Clear Hands-Free Calling, and Alexa Voice Control, Midnight Blue WH1000XM5 | Sennheiser Momentum 4 Wireless Headphones - Bluetooth Headset for Crystal-Clear Calls with Adaptive Noise Cancellation, 60h Battery Life, Customizable Sound - White |
| Brand / model | Sony / WH-1000XM5 (model no. `WH1000XM5/L`) | Sennheiser / Momentum 4 Wireless (model no. `509267`) |
| Subcategory | Over-Ear Headphones | Over-Ear Headphones |
| Variants (`asin`) in reviews | 3 | 2 |
| Reviews in dataset | 825 | 333 |
| Average rating / rating count on Amazon | 4.5 / 5,658 | 4.1 / 2,091 |
| Recorded price | $398.00 | $299.95 |

**Why these two**
- **Comparable:** both are flagship wireless over-ear noise-cancelling headphones released in 2022,
  from different brands, at a similar price. A head-to-head comparison is meaningful.
- **One listing covers the model:** many models are split across several listings in the dataset
  (e.g. Bose 700: 730 vs 2,991 reviews; Bose QC35 II: 5 listings). For these two, the chosen listing
  holds nearly all of the model's reviews (WH-1000XM5: 825 of 936; Momentum 4: 333 of 344), so every
  review of the listing can be used without sampling.
- **Right size:** 1,158 reviews in total, small enough to approve review by review and large enough
  for meaningful rates.
- **All demo aspects are discussed** (keyword check used only for selection; real labels come later):
  battery/charging 144 vs 131, noise cancelling 449 vs 154, comfort/fit 307 vs 132.
- **Ratings differ:** 1-2 star reviews are 19% (Sony) vs 26% (Sennheiser), so comparisons are
  likely to show real differences.
- **Disambiguation test case:** the dataset also contains Sony WF-1000XM5 earbuds, so a query like
  "Sony 1000XM5" should trigger a model clarification instead of a guess.

## Scope and notes
- Statistics cover **the chosen listing only**. Smaller listings of the same models are excluded
  (WH-1000XM5: 8 listings, 111 reviews; Momentum 4: 1 listing, 11 reviews).
- `rating_number` (metadata) is the rating count shown on Amazon; `review_count` is the number of
  reviews actually in this dataset. All statistics in this project use the dataset count.
- Results describe this dataset snapshot only, not Amazon as a whole.