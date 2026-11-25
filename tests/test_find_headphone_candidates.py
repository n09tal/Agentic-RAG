import gzip
import json

from ingest.find_headphone_candidates import count_reviews, extract_model, load_headphones


def write_jsonl_gz(path, records):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def test_load_headphones_keeps_headphones_and_skips_accessories(tmp_path):
    meta_path = tmp_path / "meta.jsonl.gz"
    write_jsonl_gz(meta_path, [
        {
            "parent_asin": "H1",
            "title": "Wireless Over-Ear Headphones",
            "categories": ["Electronics", "Headphones, Earbuds & Accessories",
                           "Headphones & Earbuds", "Over-Ear Headphones"],
            "details": {"Brand": "Acme", "Item model number": "AC-100"},
        },
        {
            "parent_asin": "C1",
            "title": "Headphone Case",
            "categories": ["Electronics", "Headphones, Earbuds & Accessories", "Cases"],
            "details": {},
        },
    ])

    products = load_headphones(meta_path)

    assert list(products) == ["H1"]
    assert products["H1"]["model"] == "AC-100"
    assert products["H1"]["subcategory"] == "Over-Ear Headphones"


def test_extract_model_falls_back_to_model_name():
    assert extract_model({"Item model number": "AC-100", "Model Name": "Quiet"}) == "AC-100"
    assert extract_model({"Model Name": "Quiet"}) == "Quiet"
    assert extract_model({}) == ""


def test_count_reviews_only_counts_selected_products(tmp_path):
    reviews_path = tmp_path / "reviews.jsonl.gz"
    write_jsonl_gz(reviews_path, [
        {"parent_asin": "H1"},
        {"parent_asin": "H1"},
        {"parent_asin": "X9"},
    ])

    assert count_reviews(reviews_path, {"H1"}) == {"H1": 2}