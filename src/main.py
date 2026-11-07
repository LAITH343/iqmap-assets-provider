from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.config import get_settings
from routes.router import router
from services.routing import RoutingEngineClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    app.state.routing_engine = RoutingEngineClient(settings.routing_engine_url, settings.routing_engine_timeout)
    try:
        yield
    finally:
        await app.state.routing_engine.aclose()


app = FastAPI(title="IQ-MAP Assets Provider", lifespan=lifespan)
app.include_router(router)
