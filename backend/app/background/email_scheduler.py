import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import sessionmaker

from app.background.task_runner import DocumentTaskRunner
from app.services import email_watch_service

logger = logging.getLogger(__name__)


class EmailPollScheduler:
    """Periodischer Scheduler fuer die Outlook-Ordnerueberwachung (siehe
    Briefing Kernfunktion 12) - konzeptionell getrennt vom DocumentTaskRunner
    (siehe dort), da er periodisch statt einmalig pro Dokument laeuft. Ein
    einzelner Tick prueft alle aktiven EmailWatchConfig-Zeilen und pollt nur
    die, deren eigenes Intervall abgelaufen ist (siehe
    email_watch_service.poll_due_configs) - keine dynamische Job-Verwaltung
    pro Projekt noetig, ein einziger fester APScheduler-Job genuegt.

    Jede FastAPI-App-Instanz bekommt ihren eigenen Scheduler (siehe app.state
    in main.py), analog zum DocumentTaskRunner.
    """

    def __init__(
        self,
        session_factory: sessionmaker,
        task_runner: DocumentTaskRunner,
        tick_seconds: int = 60,
    ) -> None:
        self._session_factory = session_factory
        self._task_runner = task_runner
        self._tick_seconds = tick_seconds
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        self._scheduler.add_job(
            self._tick,
            "interval",
            seconds=self._tick_seconds,
            id="email-poll-tick",
            max_instances=1,
            coalesce=True,
        )
        self._scheduler.start()

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)

    async def _tick(self) -> None:
        # Graph-Aufrufe sind blockierendes IO (httpx.get ohne async-Client) -
        # in einen Thread ausgelagert, damit der Event-Loop nicht einfriert
        # (gleiches Muster wie DocumentTaskRunner._run_one).
        await asyncio.to_thread(self._tick_sync)

    def _tick_sync(self) -> None:
        db = self._session_factory()
        try:
            email_watch_service.poll_due_configs(db, self._task_runner)
        except Exception:  # noqa: BLE001 - ein fehlerhafter Tick darf den Scheduler nie stoppen
            logger.exception("Outlook-Polling-Tick fehlgeschlagen")
        finally:
            db.close()
