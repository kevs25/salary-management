from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.exceptions import register_exception_handlers
from app.core.settings import get_settings
from app.router.main_router import main_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="ACME Salary Management", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(main_router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
