import logging

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging


configure_logging()

settings = get_settings()

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    logger.info("Health check requested")
    return {"status": "ok"}
