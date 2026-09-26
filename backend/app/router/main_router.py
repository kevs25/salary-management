from fastapi import APIRouter

from app.router.v1 import employee_router, salary_router

main_router = APIRouter(prefix="/api/v1")
main_router.include_router(employee_router.router)
main_router.include_router(salary_router.router)
