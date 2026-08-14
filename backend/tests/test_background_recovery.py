from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.models.document import Document
from app.db.models.enums import DocumentStatus
from app.main import create_app
from tests.helpers import wait_for_document_status


def test_recovery_reprocesses_document_stuck_after_simulated_crash(test_settings):
    """Simuliert einen Absturz waehrend der Verarbeitung (Dokument haengt in
    'processing') gefolgt von einem Neustart - siehe Briefing: Recovery-Logik
    beim Start darf nie einen dauerhaft haengenden Zustand erzeugen.
    """
    app1 = create_app(test_settings)
    Base.metadata.create_all(bind=app1.state.engine)

    with TestClient(app1) as client1:
        project_id = client1.post("/api/projects", json={"name": "Recovery-Test"}).json()["id"]
        created = client1.post(
            f"/api/projects/{project_id}/documents",
            json={"typ": "notiz", "titel": "N", "inhalt": "Text fuer den Recovery-Test."},
        ).json()
        ready = wait_for_document_status(client1, project_id, created["id"])
        assert ready["status"] == "ready"

        # Absturz simulieren: Status manuell auf 'processing' zuruecksetzen, so
        # als waere der Prozess genau hier beendet worden (der Worker, der das
        # Dokument bearbeitet hat, existiert nach einem echten Neustart nicht mehr).
        with app1.state.session_factory() as db:
            document = db.get(Document, created["id"])
            document.status = DocumentStatus.PROCESSING
            db.commit()
    # Das Verlassen des TestClient-Kontexts fuehrt den Lifespan-Shutdown aus -
    # der alte Task-Runner ist damit weg, wie nach einem echten Prozessende.

    # "Neustart": eine frische App-Instanz gegen dieselbe SQLite-Datei/denselben
    # Chroma-Ordner (test_settings ist unveraendert dieselbe Konfiguration).
    app2 = create_app(test_settings)
    with TestClient(app2) as client2:
        recovered = wait_for_document_status(client2, project_id, created["id"])
        assert recovered["status"] == "ready"
        assert recovered["fehlermeldung"] is None


def test_recovery_reschedules_still_pending_documents(test_settings):
    """Ein Dokument, das noch 'pending' war (z. B. weil der Worker es noch
    nicht abgeholt hatte), muss nach einem Neustart trotzdem verarbeitet werden.
    """
    app1 = create_app(test_settings)
    Base.metadata.create_all(bind=app1.state.engine)

    with TestClient(app1) as client1:
        project_id = client1.post("/api/projects", json={"name": "Recovery-Pending"}).json()["id"]
        created = client1.post(
            f"/api/projects/{project_id}/documents",
            json={"typ": "notiz", "titel": "N", "inhalt": "Noch nicht abgeholter Auftrag."},
        ).json()
        # Bewusst NICHT auf Fertigstellung warten - wir tun so, als waere die
        # App direkt nach dem Enqueue abgestuerzt, bevor der Worker startete.

    app2 = create_app(test_settings)
    with TestClient(app2) as client2:
        recovered = wait_for_document_status(client2, project_id, created["id"])
        assert recovered["status"] == "ready"
