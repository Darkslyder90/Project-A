from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.projects import router as projects_router
from app.api.routes.retrieval import router as retrieval_router
from app.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.logging import setup_logging
from app.db.session import create_engine_and_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    """App-Factory statt Modul-Singleton, damit Tests eine eigene App-Instanz
    mit eigenen (z. B. temporaeren) Settings/DB erzeugen koennen.
    """
    setup_logging()
    settings = settings or get_settings()
    settings.ensure_persistent_dirs()

    app = FastAPI(title="Project-A", version="0.1.0")

    engine, session_factory = create_engine_and_session_factory(settings.sqlalchemy_database_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(health_router, tags=["health"])
    app.include_router(projects_router)
    app.include_router(documents_router)
    app.include_router(retrieval_router)

    return app


app = create_app()
