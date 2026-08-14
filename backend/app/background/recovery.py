from sqlalchemy.orm import sessionmaker

from app.db.models.document import Document
from app.db.models.enums import DocumentStatus


def recover_stuck_documents(session_factory: sessionmaker) -> list[int]:
    """Wird einmalig beim Start aufgerufen (siehe Briefing: Recovery-Logik).

    Dokumente, die noch 'pending' sind, werden einfach erneut eingeplant.
    Dokumente, die durch einen vorherigen Absturz/Neustart dauerhaft in
    'processing'/'indexing' haengen geblieben sind, werden erkannt - der
    In-Process-Worker, der sie bearbeitet haette, existiert nach einem
    Neustart per Definition nicht mehr - und auf 'pending' zurueckgesetzt,
    damit process_document() sie idempotent von vorne aufrollt (bestehende
    Chunks werden dabei ohnehin vor dem Neuaufbau geloescht).

    Gibt die IDs aller Documents zurueck, die (erneut) eingeplant werden muessen.
    """
    db = session_factory()
    try:
        stuck = (
            db.query(Document)
            .filter(Document.status.in_([DocumentStatus.PROCESSING, DocumentStatus.INDEXING]))
            .all()
        )
        for document in stuck:
            document.status = DocumentStatus.PENDING
            document.fehlermeldung = None
        if stuck:
            db.commit()

        pending = db.query(Document.id).filter(Document.status == DocumentStatus.PENDING).all()
        return [row[0] for row in pending]
    finally:
        db.close()
