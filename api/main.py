from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.dependencies import get_settings
from api.routers import companies, data_refresh, screening, signals, watchlist


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Small Cap Analysis Terminal",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(screening.router, prefix="/api")
    app.include_router(companies.router, prefix="/api")
    app.include_router(watchlist.router, prefix="/api")
    app.include_router(data_refresh.router, prefix="/api")
    app.include_router(signals.router, prefix="/api")

    return app


app = create_app()
