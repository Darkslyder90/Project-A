# Project-A

Persönlicher Projekt-Assistent für SAP-Beratungsprojekte: Notizen, Dokumente,
Meetings, Personen und Aufgaben erfassen und per Chat (RAG mit validierten
Quellenangaben, Claude API) dazu befragen.

Die vollständige, verbindliche Spezifikation steht in [`PROJECT_BRIEFING.md`](PROJECT_BRIEFING.md).
Dieses README beschreibt den aktuellen Entwicklungsstand und die lokale
Dev-Umgebung; wird mit jedem größeren Schritt erweitert.

## Entwicklungsstand

Umsetzung erfolgt in vertikalen, lauffähigen Schritten (siehe Briefing).
Aktuell abgeschlossen:

1. ✅ Grundstruktur, DB-Modelle, Alembic-Migrationen, Healthcheck
2. ✅ Projektverwaltung (anlegen, auswählen, umbenennen/Beschreibung ändern, löschen)
3. ✅ Manuelle Textdokumente + Chunking (struktur-/sprecher-/tokenbasiert) + lokales
   Embedding + Chroma-Speicherung (synchron, kein Background-Runner vor Schritt 8)
4. ✅ Retrieval-Test ohne Claude (reine Vektorsuche über Chroma, projekt- und
   index-version-isoliert, mit UI zum manuellen Ausprobieren)
5. ✅ Claude-Chat mit validierten Quellen (Source-IDs, Prompt-Injection-Schutz,
   strikte Grounding-Regel, Refusal-Handling, API-Nutzungsprotokollierung)
6. ✅ Persistente Chat-Konversationen (mehrere Konversationen pro Projekt,
   Umbenennen/Löschen, Quellen-Snapshot mit Live-Erkennung gelöschter
   Dokumente, Nutzer-Nachricht bleibt auch bei Claude-Ausfall erhalten)
7. ✅ Datei-Upload (PDF/DOCX/TXT/MD) + Textextraktion, Duplikatserkennung
   (SHA-256, mit bewusstem "trotzdem hochladen"), sichere Dateipfade,
   Datei-Download mit korrekten Headern – nutzt dieselbe
   `process_document`-Pipeline wie manuelle Einträge (Schritt 3)
8. ✅ Asynchrone Ingestion + Status/Recovery: `process_document` läuft nicht
   mehr synchron im Request, sondern über einen sequenziellen
   Hintergrund-Worker (`asyncio.Queue`); Dokumente sind nach dem Anlegen
   sofort `pending`, das Frontend pollt den Status; Crash-Recovery beim
   Start setzt hängende `processing`/`indexing`-Dokumente zurück auf
   `pending` und stößt sie erneut an

Alle weiteren Schritte (Bildanalyse, Personen/Tasks/Meetings,
Übersichtsseiten, Settings, Export/Import, Backup/Update,
Docker/Prod-Deployment) folgen schrittweise.

## Lokale Entwicklung

Voraussetzungen: Python 3.11+ (getestet mit 3.14), Node.js 20+ (getestet mit 24).
Docker wird für die lokale Entwicklung **nicht** benötigt (nur für Prod-Deployment,
siehe späterer Abschnitt).

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements-dev.txt
copy .env.example .env   # optional, Defaults reichen meist
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Healthcheck: http://127.0.0.1:8000/health

Tests: `.venv\Scripts\python.exe -m pytest`

Hinweis: Beim ersten Anlegen eines Dokuments (bzw. beim ersten Testlauf, der
Chunking/Embedding braucht) lädt sentence-transformers das lokale
Embedding-Modell (`intfloat/multilingual-e5-base`, ca. 1 GB) einmalig nach
`data-dev/embedding-model-cache/` herunter – das kann etwas dauern, ist danach
aber dauerhaft gecacht.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Öffnet auf http://localhost:5173 – der Vite-Dev-Server proxied `/health` und
`/api` automatisch auf das lokale Backend (Port 8000, siehe `vite.config.ts`).

### Datenverzeichnisse

Lokale Dev-Daten liegen unter `data-dev/` im Repo-Root (SQLite-DB, Uploads,
Chroma, Embedding-Model-Cache, Backups) – komplett getrennt von späteren
Produktivdaten und in `.gitignore` ausgeschlossen.

## Technische Entscheidungen (Auszug)

Kurzdokumentation der eigenständig getroffenen Detailentscheidungen (siehe
Briefing-Abschnitt "Umgang mit technischen Entscheidungen"):

- **Lokales Embedding-Modell:** `intfloat/multilingual-e5-base` statt des im
  Briefing nur beispielhaft genannten `paraphrase-multilingual-mpnet-base-v2`,
  da letzteres ein hartes 128-Token-Limit hat, was für strukturbasiertes
  Chunking (lange Abschnitte/Meeting-Blöcke) zu knapp ist. e5-base unterstützt
  512 Tokens bei guter Deutsch-Performance.
- **`review_required`-Status gilt ausschließlich für Bilder.** Bei
  Text-Zusammenfassungen ist die KI-Ausgabe rein additiv und blockiert die
  Indexierung nicht (sonst Widerspruch zu "Originaltext bleibt immer Grundlage").
- **Soft-Delete über `Document.deleted_at`** (separates Timestamp-Feld) statt
  Überladung des `status`-Felds, damit `status` ausschließlich die
  Ingestion-Pipeline beschreibt.
- **`chunks.id` ist ein String (UUID4-Hex)**, kein Autoincrement-Integer, da er
  laut Briefing identisch mit der zugehörigen Chroma-Eintrags-ID sein muss.
- **`Meeting.document_id`** hat bewusst **kein** `ON DELETE CASCADE`, sondern
  eine DB-seitige Restriktion (SQLite mit `PRAGMA foreign_keys=ON`) plus
  Unique-Constraint (1:1) – verhindert versehentliches Löschen eines
  Meeting-Protokolls auf DB-Ebene, zusätzlich zur Service-seitigen Prüfung.
- **DB-Session-Wiring über `app.state`** statt Modul-globalem Singleton
  (`app/db/session.py` liefert eine Factory-Funktion), damit Tests eigene,
  isolierte Engines/Datenbanken bekommen, ohne Import-Reihenfolge-Tricks.
- **Neue Dokumente während eines laufenden Projekt-Rebuilds:** Indexierung wird
  zurückgestellt, bis der Rebuild abgeschlossen ist (kein Dual-Write in zwei
  Index-Versionen) – wird bei Umsetzung von Schritt 8/10 im Code dokumentiert.
- **Denormalisierte `meeting_datum`/`meeting_teilnehmer` an Chunks** werden bei
  Änderung der Meeting-Verknüpfung/Teilnehmerliste automatisch durch Reindex
  des einen betroffenen Documents aktualisiert (Details folgen in Schritt 11).
- **Chunking-Dispatch (Schritt 3):** Meeting-Dokumente mit erkennbaren
  Sprecherwechseln (`Name: Text` am Zeilenanfang, ≥3 Treffer) nutzen den
  Sprecher-Chunker; Texte mit Markdown-Überschriften (`#`/`##`/`###`, ≥2
  Treffer) den Struktur-Chunker; alles andere den tokenbasierten Fallback.
  Alle drei nutzen für "zu lange Abschnitte weiter unterteilen" denselben
  tokenbasierten Chunker mit Overlap, der direkt auf Token-IDs des
  Embedding-Modells arbeitet (nicht auf Wörtern) – das hält die harte
  `max_seq_length`-Grenze garantiert ein.
- **`IndexMetadata` friert Embedding-Modell/Chunking-Konfig beim ersten
  Dokument ein** (`ensure_bootstrapped`): alle weiteren Dokumente desselben
  Projekts nutzen diese eingefrorenen Werte, nicht die ggf. seither in den
  globalen Settings geänderten – verhindert gemischte Embeddings innerhalb
  einer `index_version`. Ein Wechsel wirkt erst nach explizitem Rebuild
  (folgt in einem späteren Schritt).
- **`process_document(db, document_id)`** ist bereits die im Briefing
  geforderte, eigenständig aufrufbare Pipeline-Funktion (inkl. idempotenter
  Löschung bestehender Chunks vor Neuaufbau) – Schritt 3 ruft sie nur
  synchron direkt nach dem Anlegen auf; ein Background-Task-Runner (Schritt 8)
  kann sie unverändert übernehmen.
- **Projekt-Löschung räumt jetzt auch die Chroma-Collection auf** (Nachtrag zu
  Schritt 2, da Chroma erst seit Schritt 3 existiert) – `IndexMetadata` wird
  vor dem Löschen der Projekt-Zeile gelesen, um den Collection-Namen zu
  kennen, dann DB-Zeile löschen (FK-Kaskaden), dann Uploads-Verzeichnis und
  Chroma-Collection best-effort bereinigen.
- **`retrieval/vector_search.py`** liefert nur Kern-Metadaten aus Chroma
  (chunk_id, document_id, Rang, Score); `services/retrieval_service.py`
  reichert damit aus SQLite (Chunk/Document) an – hält die im Briefing
  vorgesehene Trennung "Chroma = Vektor + Kern-Metadaten, SQLite = vollständiger
  Chunk-Datensatz" auch beim Retrieval ein, statt alles in Chroma zu duplizieren.
  Wird in Schritt 10 um den Keyword-Suchpfad (FTS5) und Fusion erweitert.
- **Claude-API-Key-Auflösung (Schritt 5):** ausschließlich der optionale
  `.env`-Fallback-Key (`CLAUDE_API_KEY`). Ein in der DB gespeicherter,
  Fernet-verschlüsselter Key kommt erst mit der vollen Settings-Verwaltung in
  Schritt 13 dazu – dann Reihenfolge DB-Key zuerst, `.env`-Key als Fallback,
  wie im Briefing beschrieben. Ohne Key liefert der Chat-Endpunkt sauber
  HTTP 503 statt eines Absturzes (siehe Briefing: "Claude-Ausfall darf App
  nicht lahmlegen") – der Rest der App bleibt unberührt nutzbar.
- **Default-Chatmodell `claude-opus-5`**, override via `.env`
  (`CLAUDE_MODEL_DEFAULT`) möglich. Wird in Schritt 13 durch eine echte
  Settings-UI ersetzt/ergänzt (`AppSettings.claude_model`).
- **Schritt 5 ist bewusst noch einzügig (kein Konversationsverlauf):** jede
  Chat-Anfrage ist in sich abgeschlossen, ohne vorherige Nachrichten als
  Kontext. Schritt 6 baut die persistente Konversation (`ChatConversation`/
  `ChatMessage`) direkt auf `chat_service.ask()` auf, indem frühere Turns aus
  der DB gelesen und der Anthropic-`messages`-Liste vorangestellt werden.
- **Retrieval für den Chat nutzt `final_k` direkt als Top-K der Vektorsuche**
  (noch kein `candidate_k`/Fusion, da Hybrid Retrieval erst Schritt 10 kommt).
- **Nutzer-Nachricht wird vor dem Claude-Aufruf committed** (Schritt 6): Schlägt
  `call_claude` fehl (z. B. kein API-Key), bleibt die gestellte Frage trotzdem
  in der Konversation erhalten – nur die Assistant-Antwort fehlt dann. Kein
  Rollback der Nutzer-Nachricht bei einem Claude-Fehler, da das Verlieren der
  gestellten Frage die schlechtere UX wäre als eine unbeantwortete Frage in
  der Historie.
- **Jede Chat-Anfrage retrievt frisch** (kein Zwischenspeichern alter Quellen):
  der Konversationsverlauf wird nur als Text an Claude mitgeschickt (Kontext),
  nie erneut durchsucht – passend zum Briefing-Grundsatz "Chatverlauf ist kein
  eigenständiger Wissensspeicher". Der System-Prompt weist Claude zusätzlich
  darauf hin, dass Source-IDs aus früheren Antworten im Verlauf sich auf andere
  Dokumente beziehen können als die in der aktuellen Antwort neu vergebenen.
- **Quellen-Snapshot in `ChatMessage.quellen`** speichert `dokumentdatum` als
  ISO-String (JSON-Spalte) – Pydantic parst das beim Lesen automatisch zurück
  in ein `date`-Feld. `geloescht` wird nicht gespeichert, sondern beim Lesen
  live berechnet (Document-Tabelle wird pro Snapshot auf Existenz geprüft).
- **Korrektur aus Schritt 1 (Bugfix in Schritt 7 entdeckt):** `Document` hatte
  ursprünglich einen `UniqueConstraint` auf `(project_id, datei_hash)`. Das
  widerspricht dem Briefing ("Upload wird gestoppt … mit Möglichkeit, bewusst
  trotzdem fortzufahren") – ein bestätigtes Duplikat muss speicherbar sein.
  Migration `931b876860b6` ersetzt den Unique-Constraint durch einen normalen
  (nicht-eindeutigen) Index; die Duplikat-Warnung wird jetzt ausschließlich im
  Service geprüft, nicht mehr über eine DB-Constraint erzwungen.
- **Sichere Upload-Pfade ohne libmagic/python-magic:** Formatprüfung über
  Dateiendungs-Allowlist + Magic-Byte-Sniffing (PDF: `%PDF-`, DOCX: ZIP-Header
  `PK\x03\x04`, TXT/MD: gültiges UTF-8) statt einer zusätzlichen
  Systemabhängigkeit, die unter Windows-Dev-Umgebungen unnötig kompliziert
  wäre. Interne Speicherpfade (`uploads/<project-id>/<document-id>/original.<ext>`)
  werden ausschließlich aus DB-IDs und der geprüften Endung gebildet – der
  Original-Dateiname fließt nie in einen Dateisystempfad ein, sondern bleibt
  reines Metadatum (`Document.dateiname`).
- **DOCX-Überschriften werden bei der Extraktion in Markdown-Präfixe (`#`/`##`)
  übersetzt**, damit der bestehende Struktur-Chunker (Schritt 3) DOCX-Gliederung
  transparent mitnutzen kann, ohne einen eigenen DOCX-Chunker zu brauchen.
- **`process_document()` extrahiert jetzt bei Bedarf selbst** (wenn `inhalt`
  noch `None` ist und `original_dateipfad` gesetzt ist) – dieselbe Pipeline
  bedient damit sowohl manuelle Einträge (Schritt 3, `inhalt` schon gesetzt)
  als auch Datei-Uploads (Schritt 7), ohne Sonderfall-Code im Aufrufer.
- **Ein einzelner sequenzieller Worker statt eines Thread-/Prozess-Pools**
  (`DocumentTaskRunner`, `asyncio.Queue` + genau ein `_worker_loop`-Task):
  vermeidet jede Nebenläufigkeitsfrage rund um den geteilten
  Embedder/Chroma-Client (Prozess-weiter Cache, siehe Schritt 3) und passt
  zum Anspruch "eine Ingestion nach der anderen" aus dem Briefing. CPU-lastige
  Arbeit (Chunking/Embedding) läuft dabei via `asyncio.to_thread` in einem
  Thread, damit der Worker den Event-Loop nicht blockiert und der Server
  parallel weiter auf Requests antworten kann. Skalierung auf mehrere Worker
  oder eine echte Queue (Redis/RQ o. Ä.) bleibt eine spätere Option, ohne dass
  `process_document(db, document_id)` sich ändern müsste.
- **Enqueue statt synchronem Aufruf:** alle drei Stellen, die vorher
  `process_document()` direkt aufgerufen haben (manuelles Anlegen, Upload,
  "erneut verarbeiten"), rufen jetzt `task_runner.enqueue(document_id)` auf;
  der Request kehrt sofort mit Status `pending` zurück. Das Frontend pollt
  (1,5 s) die Dokumentliste, solange mindestens ein Dokument in einem
  Nicht-Endzustand ist.
- **Crash-Recovery beim Start** (`recover_stuck_documents`, in der FastAPI
  `lifespan`-Funktion vor dem ersten Request ausgeführt): Dokumente, die noch
  `processing`/`indexing` sind, können nur von einem Worker stammen, der beim
  letzten Absturz/Neustart verloren ging – sie werden auf `pending`
  zurückgesetzt (inkl. Löschen einer eventuellen alten Fehlermeldung) und wie
  alle noch `pending` gebliebenen Dokumente erneut in die Queue gestellt.
  Damit kann laut Briefing kein Dokument dauerhaft in einem hängenden Zustand
  stecken bleiben.

## Persistenzstruktur

```
<DATA_DIR>/
  project-a.db
  uploads/<project-id>/<document-id>/original.<ext>
  chroma/
  embedding-model-cache/
  backups/
```

`DATA_DIR` ist in Dev standardmäßig `<repo-root>/data-dev`, in Prod wird es per
`.env`/Docker-Volume auf einen Pfad außerhalb des Containers gesetzt (z. B.
`/data`) – siehe `backend/.env.example`.
