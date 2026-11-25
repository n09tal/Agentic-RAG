from types import SimpleNamespace

import pytest

from backend.config import Settings
from backend.llm import MissingApiKeyError, embed_texts, format_document, format_query, generate_text
from backend.smoke_test import cosine_similarity, extract_quote, pick_review


def make_settings(api_key: str | None) -> Settings:
    return Settings(_env_file=None, database_url="postgresql://unused", gemini_api_key=api_key)


def test_missing_key_raises_a_clear_error():
    settings = make_settings(None)

    with pytest.raises(MissingApiKeyError, match="GEMINI_API_KEY"):
        generate_text(settings, "hello")
    with pytest.raises(MissingApiKeyError, match="GEMINI_API_KEY"):
        embed_texts(settings, ["hello"])


def test_api_key_is_hidden_when_settings_are_printed():
    settings = make_settings("secret-123")

    assert "secret-123" not in repr(settings)
    assert settings.gemini_api_key.get_secret_value() == "secret-123"


class FakeClient:
    def __init__(self, models):
        self.models = models

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_embed_texts_asks_for_one_embedding_per_text(monkeypatch):
    calls = []

    def fake_embed_content(*, model, contents, config):
        calls.append({"model": model, "contents": contents, "config": config})
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[float(i)]) for i in range(len(contents))])

    fake_client = FakeClient(SimpleNamespace(embed_content=fake_embed_content))
    monkeypatch.setattr("backend.llm.genai.Client", lambda api_key: fake_client)

    vectors = embed_texts(make_settings("key"), ["first", "second"])

    assert vectors == [[0.0], [1.0]]
    assert len(calls[0]["contents"]) == 2
    assert calls[0]["contents"][1].parts[0].text == "second"
    assert calls[0]["config"].output_dimensionality == 1536


def test_query_and_document_formats():
    assert format_query("Is it loud?") == "task: question answering | query: Is it loud?"
    assert format_document("Great sound.", "Love it") == "title: Love it | text: Great sound."
    assert format_document("Great sound.") == "title: none | text: Great sound."


def test_cosine_similarity():
    assert cosine_similarity([1.0, 0.0], [2.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 3.0]) == pytest.approx(0.0)


def test_extract_quote_reads_the_quote_line():
    reply = 'Battery life is praised.\nQUOTE: "the battery lasts forever"'

    assert extract_quote(reply) == "the battery lasts forever"
    assert extract_quote("No quote here.") == ""


def test_pick_review_finds_a_medium_length_battery_review():
    records = [
        {"review_id": "r_1", "text": "Battery is great."},
        {"review_id": "r_2", "text": "Comfortable. " * 30},
        {"review_id": "r_3", "text": "The battery easily lasts a week of commuting. " * 6},
    ]

    assert pick_review(records)["review_id"] == "r_3"