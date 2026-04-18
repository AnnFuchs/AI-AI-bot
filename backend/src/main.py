from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.router import main_router
from src.db.first_admin import create_first_admin
from src.db.seed_sources import seed_sources
from src.db.session import AsyncSessionLocal
from src.reminders.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create first admin on application startup."""
    async with AsyncSessionLocal() as session:
        await create_first_admin(session=session)
        await seed_sources(session=session)

    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(main_router, prefix='/api/v1')
