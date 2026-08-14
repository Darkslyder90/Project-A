from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.meetings import router as meetings_router
from app.api.routes.people import router as people_router
from app.api.routes.projects import router as projects_router
from app.api.routes.retrieval import router as retrieval_router
from app.api.routes.tags import router as tags_router
from app.api.routes.tasks import router as tasks_router
from app.background.recovery import recover_stuck_documents
from app.background.task_runner import DocumentTaskRunner
from app.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.logging import setup_logging
from app.db.session import create_engine_and_session_factory
from app.ingestion.pipeline import process_document


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    task_runner: DocumentTaskRunner = app.state.task_runner
    task_runner.start()

    # Recovery (siehe Briefing): Dokumente, die durch einen vorherigen
    # Absturz/Neustart haengen geblieben sind, werden erkannt und erneut
    # eingeplant, statt dauerhaft in 'processing'/'indexing' stecken zu bleiben.
    document_ids = recover_stuck_documents(app.state.session_factory)
    for document_id in document_ids:
        task_runner.enqueue(document_id)

    yield

    await task_runner.stop()


def create_app(settings: Settings | None = None) -> FastAPI:
    """App-Factory statt Modul-Singleton, damit Tests eine eigene App-Instanz
    mit eigenen (z. B. temporaeren) Settings/DB erzeugen koennen.
    """
    setup_logging()
    settings = settings or get_settings()
    settings.ensure_persistent_dirs()

    app = FastAPI(title="Project-A", version="0.1.0", lifespan=_lifespan)

    engine, session_factory = create_engine_and_session_factory(settings.sqlalchemy_database_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    # Schritt 8: In-Process-Task-Runner statt synchroner Verarbeitung im
    # Request - process_document() ist unveraendert dieselbe Funktion wie in
    # Schritt 3 (nimmt nur eine document_id entgegen, siehe Briefing).
    app.state.task_runner = DocumentTaskRunner(process_document, session_factory)

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
    app.include_router(chat_router)
    app.include_router(people_router)
    app.include_router(tasks_router)
    app.include_router(meetings_router)
    app.include_router(tags_router)

    return app


app = create_app()
