import time


def wait_for_document_status(client, project_id: int, document_id: int, *, timeout: float = 20.0) -> dict:
    """Pollt den Dokument-Status, bis ein Endzustand erreicht ist (ready/failed).

    Seit Schritt 8 laeuft die Dokumentverarbeitung asynchron im Hintergrund -
    direkt nach dem POST/Upload-Response ist ein Dokument i. d. R. noch
    'pending' oder 'processing'. Tests, die auf das Ergebnis der Verarbeitung
    angewiesen sind (Status, Chunks, Retrieval-Treffer), pollen ueber diese
    Funktion statt den alten synchronen Ablauf anzunehmen.
    """
    deadline = time.monotonic() + timeout
    last: dict | None = None
    while time.monotonic() < deadline:
        last = client.get(f"/api/projects/{project_id}/documents/{document_id}").json()
        if last.get("status") in ("ready", "failed"):
            return last
        time.sleep(0.05)
    raise TimeoutError(
        f"Document {document_id} wurde nicht innerhalb von {timeout}s fertig verarbeitet: {last}"
    )
