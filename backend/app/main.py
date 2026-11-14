import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import environmental_data, farms, history, quick_check, rotations, satellite, soil
from app.core import logging as app_logging
from app.core.config import get_settings
from app.services.warm_up import warm_up

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Start downloading demo-district data without delaying startup; requests work meanwhile.
    task = asyncio.create_task(warm_up(get_settings())) if get_settings().warm_up_demo_districts else None
    yield
    if task is not None and not task.done():
        task.cancel()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
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
    satellite.router,
)
for router in ROUTERS:
    app.include_router(router, prefix="/api")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
