from fastapi import APIRouter

from src.auth.router import router as auth_router
from src.diary.router import router as diary_router
from src.users.router import router as users_router

main_router = APIRouter()

main_router.include_router(auth_router)
main_router.include_router(users_router)
main_router.include_router(diary_router)
