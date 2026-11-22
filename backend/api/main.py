from fastapi import FastAPI

app = FastAPI(title="Agentic-RAG API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}