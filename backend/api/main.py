from typing import Annotated

from fastapi import Depends, FastAPI, Response

from backend.config import Settings, get_settings
from backend.db import database_is_reachable

app = FastAPI(title="Agentic-RAG API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    if database_is_reachable(settings.database_url):
        return {"status": "ready", "database": "ok"}
    response.status_code = 503
    return {"status": "not_ready", "database": "unreachable"}