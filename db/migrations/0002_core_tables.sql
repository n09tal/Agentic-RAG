CREATE TABLE products (
    parent_asin    TEXT PRIMARY KEY,
    title          TEXT NOT NULL,
    brand          TEXT,
    model_number   TEXT,
    category       TEXT,
    recorded_price NUMERIC(10, 2) CHECK (recorded_price >= 0)
);

COMMENT ON COLUMN products.recorded_price IS
    'Price recorded in the dataset metadata (historical), not the current price.';

CREATE TABLE reviews (
    review_id         TEXT PRIMARY KEY,
    parent_asin       TEXT NOT NULL REFERENCES products (parent_asin),
    asin              TEXT NOT NULL,
    rating            SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    reviewed_at       TIMESTAMPTZ NOT NULL,
    title             TEXT NOT NULL,
    body              TEXT NOT NULL,
    helpful_vote      INTEGER NOT NULL DEFAULT 0,
    verified_purchase BOOLEAN NOT NULL,
    review_language   TEXT NOT NULL,
    language_approved BOOLEAN NOT NULL,
    snapshot_id       TEXT NOT NULL,
    source_file       TEXT NOT NULL,
    source_line       INTEGER NOT NULL,
    label_status      TEXT NOT NULL DEFAULT 'unlabeled'
                      CHECK (label_status IN ('unlabeled', 'labeled', 'failed')),
    label_version     TEXT,
    CONSTRAINT reviews_approved_english_only CHECK (language_approved AND review_language = 'en'),
    UNIQUE (source_file, source_line)
);

CREATE INDEX reviews_parent_asin_idx ON reviews (parent_asin);

CREATE TABLE review_chunks (
    chunk_id   TEXT PRIMARY KEY,
    review_id  TEXT NOT NULL REFERENCES reviews (review_id) ON DELETE CASCADE,
    chunk_no   SMALLINT NOT NULL CHECK (chunk_no >= 1),
    char_start INTEGER NOT NULL CHECK (char_start >= 0),
    char_end   INTEGER NOT NULL CHECK (char_end > char_start),
    chunk_text TEXT NOT NULL,
    embedding  vector(1536),
    UNIQUE (review_id, chunk_no)
);

CREATE TABLE review_aspects (
    review_id      TEXT NOT NULL REFERENCES reviews (review_id) ON DELETE CASCADE,
    aspect         TEXT NOT NULL CHECK (aspect IN ('battery', 'noise_cancellation', 'comfort')),
    sentiment      TEXT NOT NULL CHECK (sentiment IN ('positive', 'negative', 'neutral', 'mixed')),
    evidence_quote TEXT NOT NULL,
    label_version  TEXT NOT NULL,
    PRIMARY KEY (review_id, aspect, label_version)
);