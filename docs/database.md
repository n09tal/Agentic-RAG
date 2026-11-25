# Database

PostgreSQL 17 with the `vector` (pgvector) and `pg_trgm` extensions. The schema is created by the
numbered SQL files in `db/migrations`, applied in order by `uv run python -m db.migrate`. Applied
migrations are recorded in `schema_migrations` with a checksum; an applied file must never be edited
(add a new migration instead).

```mermaid
erDiagram
    products ||--o{ reviews : "parent_asin"
    reviews ||--o{ review_chunks : "review_id"
    reviews ||--o{ review_aspects : "review_id"

    products {
        text parent_asin PK
        text title
        text brand
        text model_number
        text category
        numeric recorded_price "historical, not current"
    }
    reviews {
        text review_id PK
        text parent_asin FK
        text asin
        smallint rating "1-5"
        timestamptz reviewed_at
        text title
        text body "verbatim"
        text snapshot_id
        text source_file
        int source_line
        text label_status
        text label_version
    }
    review_chunks {
        text chunk_id PK
        text review_id FK
        smallint chunk_no
        int char_start
        int char_end
        text chunk_text
        vector embedding "1536 dims"
    }
    review_aspects {
        text review_id FK
        text aspect "battery / noise_cancellation / comfort"
        text sentiment "positive / negative / neutral / mixed"
        text evidence_quote
        text label_version
    }
```

| Table | Grain | Used for |
|---|---|---|
| `products` | one row per parent product | identifying products |
| `reviews` | one row per approved English review | showing the original text; counting reviews |
| `review_chunks` | one row per chunk of a review | semantic search; every chunk points back to its review and character range |
| `review_aspects` | one row per review, aspect and label version | counting reviews that mention or complain about an aspect |

## Constraints that protect the data
- `reviews_approved_english_only`: only approved English reviews can be stored.
- `UNIQUE (source_file, source_line)` on `reviews` and `UNIQUE (review_id, chunk_no)` on
  `review_chunks`: re-running an import cannot create duplicates.
- `PRIMARY KEY (review_id, aspect, label_version)` on `review_aspects`: one label per review and
  aspect within a label version; older versions are kept for comparison.
- Rating, aspect, sentiment and label status are limited to their allowed values with `CHECK`.

## Tests
Database tests use the `fresh_database_url` fixture (`tests/conftest.py`), which creates an empty
database with a random name for each test and drops it afterwards, so tests never touch development data.