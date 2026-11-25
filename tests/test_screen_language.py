from ingest.screen_language import normalize_for_detection, screen_review

ENGLISH_TEXT = "Battery lasts all day and the noise cancelling is superb."


def fake_predict(text):
    if text.startswith("Hola"):
        return "es", 0.99
    if text.startswith("Meh"):
        return "en", 0.50
    return "en", 0.97


def review(text, title="Great headphones"):
    return {"review_id": "r_1", "title": title, "text": text}


def test_clear_english_review_is_a_candidate():
    result = screen_review(review(ENGLISH_TEXT), fake_predict)

    assert result["status"] == "english_candidate"
    assert result["reasons"] == []
    assert result["text_lang"] == "en"


def test_foreign_review_needs_review():
    result = screen_review(review("Hola, el sonido es excelente y la bateria dura mucho."), fake_predict)

    assert result["status"] == "needs_review"
    assert "text_not_confident_english" in result["reasons"]


def test_low_confidence_english_needs_review():
    result = screen_review(review("Meh, they are okay I guess for the price."), fake_predict)

    assert result["reasons"] == ["text_not_confident_english"]


def test_foreign_sentence_inside_english_text_is_flagged():
    text = ENGLISH_TEXT + " Hola amigos, el producto es excelente para mi."

    result = screen_review(review(text), fake_predict)

    assert result["reasons"] == ["foreign_sentence"]


def test_short_and_empty_texts_need_review():
    assert screen_review(review("Great!"), fake_predict)["reasons"] == ["short_text"]
    assert screen_review(review(""), fake_predict)["reasons"] == ["empty_text"]


def test_only_long_foreign_titles_are_flagged():
    short_title = screen_review(review(ENGLISH_TEXT, title="Hola!"), fake_predict)
    long_title = screen_review(review(ENGLISH_TEXT, title="Hola, los mejores audifonos"), fake_predict)

    assert short_title["reasons"] == []
    assert long_title["reasons"] == ["title_not_english"]


def test_html_line_breaks_are_removed_before_detection():
    assert normalize_for_detection("Great sound.<br /><br />Comfy fit.") == "Great sound.  Comfy fit."