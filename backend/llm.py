from google import genai
from google.genai import types
from pydantic import SecretStr

from backend.config import Settings


class MissingApiKeyError(RuntimeError):
    pass


def require_key(key: SecretStr | None, env_name: str) -> str:
    if key is None or not key.get_secret_value():
        raise MissingApiKeyError(f"{env_name} is not set. Add it to .env (see .env.example).")
    return key.get_secret_value()


def gemini_client(settings: Settings) -> genai.Client:
    return genai.Client(api_key=require_key(settings.gemini_api_key, "GEMINI_API_KEY"))


def generate_text(settings: Settings, prompt: str) -> str:
    with gemini_client(settings) as client:
        response = client.models.generate_content(model=settings.gemini_model, contents=prompt)
    return response.text or ""


def format_query(question: str) -> str:
    return f"task: question answering | query: {question}"


def format_document(text: str, title: str | None = None) -> str:
    return f"title: {title or 'none'} | text: {text}"


def embed_texts(settings: Settings, texts: list[str]) -> list[list[float]]:
    with gemini_client(settings) as client:
        response = client.models.embed_content(
            model=settings.embedding_model,
            contents=[types.Content(parts=[types.Part(text=text)]) for text in texts],
            config=types.EmbedContentConfig(output_dimensionality=settings.embedding_dimensions),
        )
    return [embedding.values for embedding in response.embeddings]