from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    logger.info("app_starting", env=settings.app_env)
    yield
    logger.info("app_stopping")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

media_path = Path(settings.media_base_dir).expanduser().resolve()
media_path.mkdir(parents=True, exist_ok=True)
media_url = settings.media_base_url.strip() or "/media"
if not media_url.startswith("/"):
    media_url = f"/{media_url}"
app.mount(media_url, StaticFiles(directory=str(media_path)), name="media")


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    structlog.contextvars.clear_contextvars()
    return response


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={
            "type": "https://api.adr.local/errors/value",
            "title": "Invalid request",
            "status": 400,
            "code": "VALUE_ERROR",
            "detail": str(exc),
        },
    )


@app.get("/health/live", tags=["health"])
async def liveness() -> dict:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness() -> dict:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_v1_prefix)
