import asyncio
import logging
from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

ProcessFn = Callable[[Session, int], None]


class DocumentTaskRunner:
    """Einfache In-Process-Queue statt externer Job-Queue (siehe Briefing:
    "Fuer den MVP genuegt eine einfache Background-Task-Loesung... statt
    einer externen Job-Queue"). Genau ein sequenzieller Worker: die
    Ingestion-Pipeline nutzt Prozess-weite Singletons (Embedder,
    Chroma-Client), sequenzielle Verarbeitung vermeidet jede Nebenlaeufigkeits-
    frage dort, ohne fuer eine Single-User-App Durchsatz zu kosten, der
    tatsaechlich gebraucht wuerde.

    Jede FastAPI-App-Instanz bekommt ihren eigenen Runner (siehe app.state in
    main.py), damit Tests/Dev/Prod sich nie gegenseitig beeinflussen.

    `process_fn` wird pro Auftrag in einem eigenen Thread ausgefuehrt
    (asyncio.to_thread) - Chunking/Embedding ist CPU-gebunden und wuerde sonst
    den Event-Loop blockieren und alle anderen Requests einfrieren lassen.
    """

    def __init__(self, process_fn: ProcessFn, session_factory: sessionmaker) -> None:
        self._process_fn = process_fn
        self._session_factory = session_factory
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        if self._worker_task is None:
            return
        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass
        self._worker_task = None

    def enqueue(self, document_id: int) -> None:
        self._queue.put_nowait(document_id)

    async def wait_until_idle(self) -> None:
        """Nur fuer Tests/Diagnose: wartet, bis die Warteschlange leergelaufen ist."""
        await self._queue.join()

    async def _worker_loop(self) -> None:
        while True:
            document_id = await self._queue.get()
            try:
                await asyncio.to_thread(self._run_one, document_id)
            except Exception:  # noqa: BLE001 - ein fehlerhafter Auftrag darf den Worker nie beenden
                logger.exception("Verarbeitung von Document %s fehlgeschlagen", document_id)
            finally:
                self._queue.task_done()

    def _run_one(self, document_id: int) -> None:
        db = self._session_factory()
        try:
            self._process_fn(db, document_id)
        finally:
            db.close()
