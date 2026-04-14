# from contextlib import asynccontextmanager
# from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.router import main_router

# from src.db.first_admin import create_first_admin
# from src.db.session import AsyncSessionLocal


# @asynccontextmanager
# async def lifespan(app: FastAPI) -> AsyncIterator[None]:
#     """Создание админа на старте приложения."""
#     async with AsyncSessionLocal() as session:
#         await create_first_admin(session=session)
#     yield


app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    # lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(main_router, prefix='/api/v1')
