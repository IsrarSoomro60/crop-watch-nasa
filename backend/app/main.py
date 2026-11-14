from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import environmental_data, farms, history, quick_check, rotations, soil
from app.core import logging as app_logging
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app_logging.setup(app, settings.log_level)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROUTERS = (
    farms.router,
    environmental_data.router,
    soil.router,
    rotations.router,
    history.router,
    quick_check.router,
)
for router in ROUTERS:
    app.include_router(router, prefix="/api")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
