import asyncio
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.background.task_runner import DocumentTaskRunner


@pytest.mark.asyncio
async def test_task_runner_processes_enqueued_ids_sequentially():
    engine = create_engine("sqlite:///:memory:")
    session_factory = sessionmaker(bind=engine)

    processed: list[int] = []

    def fake_process(_db, document_id: int) -> None:
        # Absichtlich synchron "langsam", um zu pruefen, dass Auftraege nacheinander
        # (nicht parallel) verarbeitet werden - siehe Docstring in task_runner.py.
        time.sleep(0.05)
        processed.append(document_id)

    runner = DocumentTaskRunner(fake_process, session_factory)
    runner.start()
    try:
        for doc_id in (1, 2, 3):
            runner.enqueue(doc_id)
        await asyncio.wait_for(runner.wait_until_idle(), timeout=5)
    finally:
        await runner.stop()

    assert processed == [1, 2, 3]


@pytest.mark.asyncio
async def test_task_runner_continues_after_a_failing_job():
    engine = create_engine("sqlite:///:memory:")
    session_factory = sessionmaker(bind=engine)

    processed: list[int] = []

    def fake_process(_db, document_id: int) -> None:
        if document_id == 2:
            raise RuntimeError("simulierter Fehler")
        processed.append(document_id)

    runner = DocumentTaskRunner(fake_process, session_factory)
    runner.start()
    try:
        for doc_id in (1, 2, 3):
            runner.enqueue(doc_id)
        await asyncio.wait_for(runner.wait_until_idle(), timeout=5)
    finally:
        await runner.stop()

    # Auftrag 2 ist fehlgeschlagen, aber der Worker darf dadurch nicht sterben -
    # Auftrag 3 muss trotzdem noch verarbeitet werden.
    assert processed == [1, 3]
