from fastapi import APIRouter

from app.router.v1 import employee_router

main_router = APIRouter(prefix="/api/v1")
main_router.include_router(employee_router.router)
