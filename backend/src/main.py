from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from src.core.config import settings
from src.core.router import main_router
from src.db.first_admin import create_first_admin
from src.db.session import AsyncSessionLocal
from src.reminders.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create first admin on application startup."""
    async with AsyncSessionLocal() as session:
        await create_first_admin(session=session)

    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    lifespan=lifespan,
)

app.include_router(main_router, prefix='/api/v1')
