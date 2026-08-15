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
9. ✅ Bildanalyse + Review-Schritt: Bild-Upload (PNG/JPG) löst eine
   Claude-Vision-Analyse aus (`ocr_text`/`ki_analyse_rohtext` getrennt
   gespeichert), Dokument bleibt danach im Status `review_required` stehen;
   erst nach Bestätigung/Bearbeitung durch den Nutzer wird der Text als
   `inhalt` übernommen und indexiert – Chunking/Embedding sehen bei Bildern
   ausschließlich die bestätigte Fassung, nie die Roh-KI-Ausgabe direkt
10. ✅ Hybrid Retrieval mit FTS5: paralleler Keyword-/Volltextsuchpfad über
    einen SQLite-FTS5-Index (`chunk_fts`, automatisch per Trigger synchron
    zu `chunks`) ergänzt die bestehende Vektorsuche; beide Kandidatenlisten
    werden per Reciprocal Rank Fusion kombiniert (inkl. Passthrough-
    Rerank-Schnittstelle für später) und liefern u. a. exakte Treffer für
    SAP-Transaktionscodes/Tabellen/Ticketnummern zuverlässig, auch wenn
    Embeddings dort schwächeln; Chat und Retrieval-Test-Ansicht nutzen
    denselben `hybrid_search()`-Pfad
11. ✅ Personen/Tasks/Meetings: vollständiges CRUD inkl. der im Datenmodell
    geforderten Join-Tabellen (`TaskDocument`, `MeetingParticipant`);
    Personen-Löschung setzt Task-Zuweisungen auf `NULL` und entfernt
    Meeting-Teilnahmen (DB-FK-Kaskaden); ein Meeting kann optional ein
    Protokoll-Dokument tragen – ist eines gesetzt, kann es nicht separat
    gelöscht werden, nur über das Löschen des gesamten Meetings (das dann
    sein Dokument mitentfernt) – dafür jetzt auch generische
    Dokument-Löschung (Soft-Delete + Chroma-/Chunk-/Datei-Cleanup)
12. ✅ Übersichtsseiten: neuer Reiter-Umschalter ("Übersicht" / "Chat" /
    "Verwalten") statt einer langen Seite; "Übersicht" zeigt kompakte
    Tabellen für Dokumente (inkl. Tags, Status-Badge, Bild-Vorschau/Volltext
    per Klick aufklappbar), Personen (inkl. zugehöriger Aufgaben), Aufgaben
    (inkl. zugewiesener Person/verknüpfter Dokumente) und Meetings (inkl.
    Teilnehmer/Protokoll-Auszug); "Verwalten" enthält die bisherigen
    Formulare/Listen (inkl. der jetzt wieder eingebundenen Aufgaben-Section);
    "Chat" bündelt Chat + Retrieval-Test. Dabei nachgezogen: minimale
    Tag-Verwaltung (bisher nur Datenmodell, nie an eine UI angebunden)
13. ✅ Settings: globale Einstellungsseite (eigener Reiter-übergreifender
    Bereich, kein Projektbezug) – Claude-API-Key verschlüsselt in SQLite
    (Fernet, Klartext nie im UI/Log), maskierte Anzeige, `.env`-Fallback,
    Claude-Chatmodell unabhängig vom Embedding-Modell wählbar, RAG-Feintuning
    (candidate_k je Suchpfad, final_k, Chunk-Zielgröße/Overlap – wirkt sofort
    auf neue Retrieval-Anfragen), kompakte API-Nutzungsübersicht (heute/
    Woche/Monat, Anfragen + Tokens)
14. ✅ Export/Import: Projekt-Export als ZIP (versioniertes Manifest +
    `data.json` mit Documents/Personen/Tasks/Meetings/Tags/Chats +
    Originaldateien), bewusst ohne Claude-API-Key/globale Settings/Chunks
    (abgeleitet, siehe Source-of-Truth-Prinzip). Import legt immer ein neues
    Projekt mit komplett neu vergebenen IDs an (durchgängiges Remapping aller
    Fremdschlüssel, inkl. Quellen-Snapshots im Chatverlauf), ist transaktional
    (Fehler mitten im Import räumt DB-Änderungen und bereits kopierte Dateien
    wieder auf) und Zip-Slip-geschützt; nach erfolgreichem Import wird jedes
    Dokument automatisch neu indexiert (Chroma ist für das neue Projekt
    zunächst leer)
15. ✅ Backup/Update/Recovery + Docker Compose: konsistenzsicheres Backup
    (SQLite `VACUUM INTO` + Uploads, bewusst ohne Chroma/Encryption-Secret,
    Aufbewahrung der letzten 10 automatischen Backups) als eigenständiges
    Skript (`backend/scripts/backup.py`); `scripts/update.sh` fasst den im
    Briefing vorgeschriebenen Update-Ablauf zusammen (Backup → `git pull` →
    Images bauen → Migration **einmalig kontrolliert** → Start → Healthcheck);
    Produktiv-Deployment per `docker-compose.yml` (Backend + statisch
    ausgeliefertes Frontend + Caddy als Reverse Proxy mit automatischem HTTPS
    + Basic Auth). Healthcheck (SQLite/Verzeichnisse, kein Claude-Aufruf) war
    bereits seit Schritt 1 vorhanden.

Damit sind alle 15 im Briefing beschriebenen vertikalen Schritte umgesetzt.

### Nachträge nach Abschluss der 15 Schritte

Zusätzliche, vom Nutzer nachträglich gewünschte Funktionen (nicht Teil der
ursprünglichen 15 Schritte):

- **Quellen im Chat sind jetzt direkt aufklappbar**: Klick auf eine
  Quellenangabe `[S1]` lädt und zeigt das zitierte Dokument inline (Volltext,
  bei Bildern Vorschau, Download-Link bei hochgeladenen Dateien) – ohne
  Tab-Wechsel zur Übersicht.
- **Spracheingabe beim manuellen Anlegen von Dokumenten**: Mikrofon-Button
  über dem Inhaltsfeld nutzt die Web Speech API des Browsers (Chrome/Edge;
  Firefox/Safari unterstützen das nicht zuverlässig, Button wird dort
  automatisch ausgeblendet). Wichtig für die Datenschutz-Transparenz des
  Projekts: die Spracherkennung läuft dabei **nicht** über Project-A's
  eigenen Server, sondern über den Spracherkennungsdienst des
  Browser-Anbieters (z. B. Google bei Chrome) – im UI als Hinweis während
  der Aufnahme sichtbar.
- **API-Kostenschätzung**: neue `ModelPricing`-Tabelle (Preise pro Modell,
  zeitlich versioniert über `gueltig_ab`) plus manuell gepflegter
  EUR/USD-Wechselkurs (`AppSettings.eur_usd_wechselkurs`, kein automatischer
  Kursabruf). Die API-Nutzungsübersicht in den Einstellungen zeigt damit
  zusätzlich zu Anfragen/Tokens eine grobe Kostenschätzung
  ("ca. 1,42 €") pro Zeitraum. Kosten werden dabei **immer live** aus
  Tokens + dem zum jeweiligen Zeitpunkt gültigen Preis berechnet, nie
  dauerhaft als Euro-Betrag gespeichert – historische Auswertungen bleiben
  dadurch korrekt, auch wenn sich Preise später ändern. Fehlt für einen
  genutzten Modellnamen ein Preis, wird das per `vollstaendig: false` und
  einem "unvollständig"-Hinweis in der UI transparent gemacht, statt eine
  falsch-genaue Zahl vorzutäuschen. Startwerte für `claude-opus-5`,
  `claude-sonnet-5` und `claude-haiku-4-5-20251001` sind mit den zum
  Einspielzeitpunkt der Migration (14.08.2026) aktuellen Preisen vorbefüllt.
  **Hinweis:** der vorbefüllte Wechselkurs (0,92) ist ein grober Platzhalter
  ohne Anbindung an eine Live-Kursquelle – bitte in den Einstellungen mit
  dem tatsächlich aktuellen Kurs überschreiben.

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

## Deployment (Produktion)

Produktiv läuft Project-A per `docker compose` auf einem eigenen VPS – lokale
Entwicklung nutzt bewusst **kein** Docker (siehe oben). Drei Container:

- **backend** – FastAPI (`backend/Dockerfile`), Healthcheck ruft ausschließlich
  `/health` auf (kein Claude-Aufruf, siehe Briefing).
- **frontend** – gebauter React-Build, statisch per nginx ausgeliefert
  (`frontend/Dockerfile`).
- **caddy** – Reverse Proxy mit automatischem HTTPS (Let's Encrypt) + Basic
  Auth vor der gesamten App (siehe Briefing: "Server ist öffentlich erreichbar").
  Leitet `/api/*` und `/health` an `backend`, alles andere an `frontend` weiter.

### Erststart

```bash
git clone <repo-url> project-a
cd project-a
cp .env.example .env        # DOMAIN, BASIC_AUTH_*, SETTINGS_ENCRYPTION_KEY setzen
docker compose build
docker compose run --rm backend alembic upgrade head
docker compose up -d
```

`SETTINGS_ENCRYPTION_KEY` erzeugen mit:
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
`BASIC_AUTH_PASSWORD_HASH` erzeugen mit:
`docker run --rm caddy caddy hash-password --plaintext 'dein-passwort'`

**Encryption-Secret (wichtig):** `SETTINGS_ENCRYPTION_KEY` bleibt bewusst
außerhalb der SQLite-Datenbank und ist **nicht** Teil der automatischen
Update-Backups (siehe unten) oder eines Projekt-Exports. Separat sicher
aufbewahren (z. B. Passwortmanager) – geht der Schlüssel verloren, ist ein in
der DB gespeicherter Claude-API-Key nicht mehr entschlüsselbar und muss in
den Einstellungen neu eingegeben werden. Alle übrigen Daten (Dokumente,
Personen, Tasks, Chats etc.) sind davon unberührt.

### Updates

```bash
./scripts/update.sh
```

Führt in fester Reihenfolge aus (siehe Briefing "Updates, Migrationen,
Backup & Healthcheck"): Backup → `git pull` → Images bauen → `alembic upgrade
head` (einmalig, kontrolliert, nicht parallel aus mehreren Containern) →
`docker compose up -d` → Healthcheck. Schlägt die Migration fehl, bricht das
Skript ab, bevor die neue Anwendung gestartet wird – die vorherige,
funktionierende Version läuft unverändert weiter.

## Backup & Restore

Ein Backup enthält die konsistent gesicherte SQLite-Datenbank (`VACUUM INTO`,
keine rohe Dateikopie einer möglicherweise gerade beschriebenen Datei) sowie
alle hochgeladenen Originaldateien, gepackt als Zeitstempel-ZIP unter
`<DATA_DIR>/backups/`. **Nicht** enthalten: Chroma (aus SQLite + Originalen
jederzeit rekonstruierbar) und `SETTINGS_ENCRYPTION_KEY` (siehe oben).
Automatische Backups behalten standardmäßig die letzten 10 (ältere werden
beim nächsten Backup entfernt).

- Manuell/per Cron: `./scripts/backup.sh`
- Automatisch vor jedem Update: Teil von `scripts/update.sh` (siehe oben)

**Restore** ist im MVP ein manueller Vorgang (kein eigener Restore-Befehl):
Anwendung stoppen (`docker compose down`), Backup-ZIP entpacken, `project-a.db`
und `uploads/` in das `DATA_DIR`-Volume zurückkopieren, Anwendung neu starten.
Die zurückgesicherte DB enthält weiterhin ihre `chunks`/`chunk_fts`-Einträge,
daher funktioniert die Volltextsuche im Chat sofort wieder; nur falls das
Chroma-Verzeichnis selbst nicht mit zurückgesichert wurde (z. B. Datenverlust
nur dort), liefert der Vektor-Suchpfad bis dahin keine Treffer – **ein
automatischer Rebuild bei leerem/fehlendem Chroma ist im MVP noch nicht
eingebaut** (das im Briefing beschriebene "Gesamtes Projekt neu indexieren"
bleibt zukünftige Arbeit). Übergangsweise pro betroffenem Dokument auf
"Erneut verarbeiten" klicken (siehe Übersichtsseite) – das baut sowohl
Chroma-Vektoren als auch `chunks`/`chunk_fts` für dieses eine Dokument
sauber neu auf (`process_document()` löscht vorhandene Chunks der aktiven
Index-Version idempotent und erzeugt sie neu).

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
- **Bild-Analyse als fester Zwischenstopp in `process_document()`, nicht als
  eigener Pipeline-Pfad** (Schritt 9): Ist `typ == bild` und `inhalt` noch
  `None`, wird die Vision-Analyse ausgeführt, `ocr_text`/`ki_analyse_rohtext`
  gesetzt, Status auf `review_required` gesetzt und die Funktion kehrt zurück
  – Chunking/Embedding laufen bewusst nicht in demselben Durchlauf. Bestätigt
  der Nutzer die Analyse (`confirm_image_review`), wird `inhalt` gesetzt,
  Status auf `pending` zurückgesetzt (wie bei `reprocess_document`) und
  `process_document()` erneut eingereiht: `inhalt` ist dann bereits gesetzt,
  die Funktion überspringt Extraktion/Vision-Analyse komplett und indexiert
  direkt – dieselbe idempotente Funktion bedient damit alle drei Eingabewege
  (manueller Text, Datei-Upload, Bild-Review), ohne Sonderfall-Code im
  Background-Task-Runner.
  **Bugfix nach erstem Nutzer-Test:** ursprünglich blieb der Status nach der
  Bestätigung auf `review_required` stehen (kein Wechsel auf einen der vom
  Frontend aktiv gepollten Status) – da die Hintergrund-Indexierung oft
  schneller fertig ist, als das Frontend reagieren kann, zeigte die
  Review-Ansicht dann faelschlich weiter das (bereits erledigte) Panel an,
  und ein zweiter Bestätigungsversuch schlug mit 409 fehl. Der Wechsel auf
  `pending` behebt das, ohne dass das Frontend selbst etwas Besonderes tun
  muss (`pending` ist ohnehin schon ein aktiv gepollter Status).
- **Antwortformat der Vision-Analyse:** feste Zwei-Block-Struktur
  (`<ocr_text>…</ocr_text><analyse>…</analyse>`) statt eines
  JSON-Schemas/Structured-Output-Constraints – reicht für den MVP, bleibt
  aber lesbar/robust: liefert Claude nicht exakt dieses Format, landet die
  volle, ungeparste Antwort trotzdem nutzbar in `ki_analyse_rohtext`
  (`ocr_text` bleibt dann leer) statt den Task fehlschlagen zu lassen – kein
  Blackbox-Fehler nur wegen eines Formatierungsabweichlers.
- **`typ` wird bei Bild-Uploads serverseitig auf `bild` erzwungen**
  (`document_service.create_uploaded_document`), unabhängig davon, was das
  Formular mitschickt – verhindert einen inkonsistenten Zustand, in dem ein
  Bild z. B. als `notiz` markiert ist und die Pipeline dadurch fälschlich den
  Text-Extraktionspfad statt der Vision-Analyse waehlt.
- **Bild-Magic-Bytes ergänzen dieselbe libmagic-freie Prüfung wie Schritt 7:**
  PNG-Signatur `\x89PNG\r\n\x1a\n`, JPEG-Signatur `\xff\xd8\xff` – gleiche
  Begründung (keine zusätzliche Systemabhängigkeit für Windows-Dev).
- **`chunk_fts` als FTS5-"external content"-Tabelle über `chunks.rowid`**
  (Schritt 10), nicht als eigenständige Tabelle mit dupliziertem Text:
  spart Speicher und hält die Source-of-Truth-Regel ein (Chunk-Text lebt nur
  einmal, in `chunks`). SQLites impliziter `rowid` existiert auch bei einem
  TEXT-Primary-Key wie `Chunk.id` (UUID) und ist als `content_rowid`
  verwendbar, ohne eine zusätzliche Integer-Spalte einzuführen.
- **Synchronisierung über SQL-Trigger statt Anwendungscode** (`chunks_fts_ai`/
  `_ad`/`_au`, angelegt in Migration `c7e2a1f4d9b3`): haelt `chunk_fts`
  garantiert konsistent zu `chunks`, unabhängig vom Codepfad (`process_document`,
  `_cleanup_existing_chunks`, oder ein DB-seitiges `ON DELETE CASCADE` bei
  Dokument-Löschung) – robuster als eine Pflege an mehreren Stellen im
  Python-Code, die leicht auseinanderlaufen könnte.
- **`chunk_fts` ist kein ORM-Modell und daher nicht Teil von `Base.metadata`:**
  Tests, die das Schema direkt aus `Base.metadata.create_all()` erzeugen (ohne
  Alembic zu durchlaufen, siehe `tests/conftest.py`), rufen zusätzlich
  `app/db/fts_setup.py::ensure_chunk_fts()` auf – dieselbe (idempotente) DDL
  wie in der Migration, bewusst als eigene Kopie gehalten statt die Migration
  zu importieren, damit Migrationen ein eingefrorener historischer Schritt
  bleiben. `alembic/env.py` filtert `chunk_fts`/ihre SQLite-Schattentabellen
  (`_data`/`_idx`/`_docsize`/`_config`) zusätzlich per `include_object` aus
  dem Autogenerate-/`alembic check`-Vergleich heraus, sonst würde jeder Check
  fälschlich vorschlagen, sie wieder zu löschen.
- **Keyword-Suche baut MATCH-Anfragen aus einzeln in Anführungszeichen
  gesetzten, mit OR verknüpften Tokens** (`retrieval/keyword_search.py`)
  statt rohen Nutzertext direkt an FTS5 MATCH zu übergeben – schützt vor
  FTS5-Syntaxfehlern durch Sonderzeichen/reservierte Operatoren (`-`, `:`,
  `AND`/`OR`/`NOT`/`NEAR`) im Suchtext.
- **Fusion ausschließlich rangbasiert (Reciprocal Rank Fusion, `k=60`)**,
  wie im Briefing gefordert – Vektor-Cosine-Similarity und BM25-Scores liegen
  auf nicht vergleichbaren Skalen und werden nirgends direkt addiert.
- **Rerank-Schnittstelle als eigenes, bewusst leeres Modul**
  (`retrieval/reranker.py`, Passthrough) – definierte Signatur
  (Kandidatenliste + Query rein → Liste raus) für einen späteren lokalen
  Cross-Encoder, ohne `hybrid_search()` umbauen zu müssen.
- **`candidate_k_vector`/`candidate_k_keyword` kommen live aus den globalen
  RAG-Settings, nicht aus der am Index eingefrorenen Konfiguration** (anders
  als Embedding-Modell/Chunking) – sie sind reine Retrieval-Zeit-Parameter
  und beeinflussen nicht, wie der Index aufgebaut wurde.
- **Generische Dokument-Löschung erst in Schritt 11 nachgezogen** (Soft-Delete
  über `Document.deleted_at`, danach best-effort Cleanup von
  TaskDocument-Zeilen, Chunks, Chroma-Vektoren, Originaldatei): das Briefing
  ordnet Löschregeln zwar Punkt 6 zu, ein konkreter Endpunkt war aber bis
  Schritt 11 nicht nötig – Meeting-Löschung (siehe unten) braucht ihn jetzt
  zwingend, da das Pflicht-Dokument eines Meetings im selben Vorgang mit
  entfernt werden muss.
- **`Task.dokument_ids`/`Meeting.teilnehmer_ids` als reine Lese-Properties**
  über `viewonly=True`-Relationships (`secondary=task_documents` bzw.
  `secondary=meeting_participants`), nicht als eigenes DTO: Pydantics
  `from_attributes=True` liest normale Python-Properties genauso wie
  gemappte Spalten, damit bleiben `TaskRead`/`MeetingRead` einfache
  Ein-Objekt-Serialisierungen ohne manuelles Zusammenbauen im Service. Die
  eigentliche Pflege der Verknüpfung läuft weiterhin explizit über
  `link_document`/`unlink_document` bzw. `add_participant`/`remove_participant`
  (keine automatische Synchronisierung über die Relationship selbst).
- **Meeting-Löschung: Reihenfolge Meeting zuerst, dann Dokument** – die
  Meeting-Zeile muss aus der DB verschwunden sein, bevor
  `document_service.delete_document()` aufgerufen wird, sonst blockiert dessen
  eigene Meeting-Pflicht-Prüfung die Löschung des soeben verwaisten Dokuments.
- **Task-/Meeting-Verknüpfungen proaktiv gegen Projektgrenzen geprüft**
  (`zugewiesen_an`, `dokument_ids`, `teilnehmer_ids`, `document_id`): jede
  referenzierte Person/jedes referenzierte Dokument muss zum selben Projekt
  gehören, sonst `422`/`404` statt eines stillen Cross-Project-Links (siehe
  Briefing: "Projektgrenzen strikt erzwingen").
- **Ein Dokument, das bereits das Protokoll eines Meetings ist, kann kein
  zweites Meeting mehr bekommen** – proaktiv geprüft (`409` mit Verweis auf
  das bestehende Meeting) statt den DB-`UNIQUE`-Constraint auf
  `Meeting.document_id` als rohen `IntegrityError` durchschlagen zu lassen.
- **Korrektur nach Nutzer-Feedback: `Meeting.document_id` ist nachträglich
  nullable geworden** (Migration `43ad9f389ced`) – ursprünglich als
  Pflichtfeld analog zum Briefing-Vorschlag umgesetzt, auf ausdrücklichen
  Wunsch aber auf "Meeting auch ohne Protokoll anlegbar" geändert. SQLite
  erlaubt mehrere `NULL`-Werte in einer `UNIQUE`-Spalte, die 1:1-Regel
  (höchstens ein Meeting pro Dokument) bleibt daher für tatsächlich gesetzte
  Werte weiterhin über den Unique-Index erzwungen. `MeetingUpdate` erlaubt
  jetzt zusätzlich, ein Protokoll-Dokument nachträglich zuzuweisen; die
  Löschung eines Meetings ohne Dokument überspringt einfach den
  `document_service.delete_document()`-Aufruf.
- **Aufgaben-Abschnitt auf der Projektseite auf Nutzerwunsch kurzzeitig
  entfernt, in Schritt 12 mit dem neuen Verwalten-Tab wieder eingebunden**
  (siehe Klärung zu Beginn von Schritt 12 – der Nutzer wollte Tasks nicht
  lose auf der langen Seite, aber ausdrücklich in der neuen
  Übersichtsseite).
- **Übersichtsseiten als Reiter-Layout statt einer noch längeren Seite**
  (`ProjectHome.tsx` bekommt einen simplen Tab-State `uebersicht|chat|
  verwalten`, keine Router-Bibliothek eingeführt – für drei feste Reiter
  innerhalb eines Projekts reicht lokaler State, eine URL-Route pro Tab
  bringt für den Single-User-MVP keinen Mehrwert): Klärung mit dem Nutzer
  ergab "eigener Tab/Reiter" gegenüber "alles weiter untereinander".
- **Tags nachgezogen** (`Tag`/`DocumentTag` existierten seit Schritt 1 im
  Datenmodell, waren aber nie an eine UI oder einen Endpunkt angebunden) –
  minimal gehalten: `get_or_create_tag()` beim Zuweisen (kein separates
  Tag-Verwaltungsformular), Tags werden nur über ein Dokument herum
  vergeben/entfernt (`POST/DELETE .../documents/{id}/tags`), Löschen eines
  Tags selbst über `DELETE .../tags/{id}` entfernt ihn aus allen Dokumenten
  (FK-Kaskade auf `document_tags`). `Document.tag_ids` als viewonly-
  Relationship-Property, analog zu `Task.dokument_ids`/`Meeting.teilnehmer_ids`.
- **`delete_document()` räumt jetzt zusätzlich `DocumentTag`-Zeilen auf**
  (Nachtrag zu Schritt 11/12, analog zur bereits vorhandenen
  `TaskDocument`-Bereinigung) – beim Soft-Delete greift die FK-Kaskade
  nicht, da die Document-Zeile selbst nicht gelöscht wird.
- **"Klick öffnet Volltext" als aufklappbare Tabellenzeile** statt eines
  Modals/einer Detailseite – reicht für die "einfache tabellarische
  Übersicht" laut Briefing, ohne zusätzliches Routing/State-Management für
  eine Dokumentendetailseite einzuführen.
- **`.app-shell` max-width von 640px auf 900px erhöht**, damit die
  mehrspaltigen Übersichtstabellen nicht zu gedrängt wirken; einzelne
  Tabellen bekommen zusätzlich `overflow-x: auto`, falls der Inhalt trotzdem
  nicht passt (schmale Fenster/viele Tags).
- **Verschlüsselung als eigenes, kleines Modul** (`security/crypto.py`,
  Fernet) statt Inline-Code in `settings_service.py` – `decrypt()` liefert
  bewusst `None` statt einer Exception bei falschem/fehlendem Secret, damit
  ein nicht mehr entschlüsselbarer gespeicherter Key als sauberer
  `db_invalid`-Status behandelt wird statt eines 500ers (siehe Briefing:
  "geht das Secret verloren, muss der Key neu eingegeben werden").
- **Kein Klartext-Key jemals im Response-Body** – `AppSettingsRead` enthält
  ausschließlich `claude_api_key_status` + eine maskierte Kurzform
  (`sk-ant-…xxxx`), auch direkt nach dem Speichern eines neuen Keys.
- **Leerer String bei `claude_api_key` im PATCH = "gespeicherten Key
  entfernen"** (fällt zurück auf `.env`), fehlendes Feld = unverändert
  lassen – dieselbe `model_fields_set`-Unterscheidung wie bei den anderen
  PATCH-Endpunkten, hier zusätzlich für den Spezialfall "auf null setzen
  bedeutet etwas anderes als weglassen".
- **`claude_client._resolve_api_key()`/Modellwahl lesen jetzt live aus der
  DB** (`settings_service.resolve_effective_claude_api_key/_model`) statt
  nur aus `.env` (Schritt 5-Platzhalter) – Reihenfolge wie im Briefing:
  DB-Key zuerst, `.env`-Key als Fallback; ein nicht entschlüsselbarer
  DB-Key zählt dabei wie "kein Key vorhanden", nicht wie ein harter Fehler.
- **`fusion_verfahren` in der Settings-UI bewusst nur informativ angezeigt
  (deaktiviertes Feld), nicht editierbar** – aktuell existiert einzig
  Reciprocal Rank Fusion als Implementierung; ein editierbares Auswahlfeld
  ohne zweite Implementierung dahinter würde eine nicht vorhandene
  Funktionalität vortäuschen.
- **Kein automatischer Reindex-Hinweis/-Button bei geänderten Embedding-/
  Chunking-Settings in Schritt 13** – die dafür nötige Blue/Green-
  Neuindexierung (siehe Briefing) ist bewusst ein eigenständiges, noch
  ausstehendes Stück Funktionalität; die Settings-UI weist stattdessen nur
  im Hilfetext darauf hin, dass Änderungen sich nicht auf bereits aktive
  Indizes auswirken.
- **Genereller Testisolations-Fix:** `tests/conftest.py` wechselt das
  Arbeitsverzeichnis der `test_settings`-Fixture jetzt per
  `monkeypatch.chdir(tmp_path)` in ein leeres Verzeichnis. Vorher konnte ein
  reales `backend/.env` (z. B. mit einem echten Claude-Key oder einem
  individuell gesetzten `CLAUDE_MODEL_DEFAULT` für die lokale Dev-Nutzung)
  in jedes Testfeld durchsickern, das ein Test nicht explizit selbst setzt –
  das ist bereits zweimal als echtes Leck aufgefallen (unbeabsichtigter
  echter API-Call in einem Test, ein Modell-Settings-Test schlug lokal fehl).
  Jetzt sehen Tests ausschließlich Klassen-Defaults + explizit gesetzte
  Env-Vars, nie die tatsächliche `.env`-Datei.
- **Export-Format als ZIP mit `manifest.json` + `data.json` statt eines
  SQLite-Auszugs** – die Datenstruktur zwischen App-Versionen kann sich
  ändern, ein versioniertes, lesbares JSON-Format lässt sich beim Import
  gezielt migrieren/ablehnen (`manifest.version` wird geprüft), ein rohes
  SQLite-Fragment wäre an interne Schema-Details der exportierenden Version
  gebunden.
- **Chunks werden nie exportiert/importiert** (siehe Source-of-Truth-Prinzip:
  abgeleitete, jederzeit rekonstruierbare Indexdaten) – nach jedem Import
  wird automatisch eine vollständige Neuindexierung angestoßen, indem alle
  importierten Dokumente ganz normal über den bestehenden
  `DocumentTaskRunner`/`process_document()`-Pfad eingereiht werden. Da das
  neue Projekt naturgemäß noch keinen aktiven Index hat, ist dafür keine
  Blue-/Green-Rebuild-Logik nötig (die für das *Neuindexieren eines bereits
  aktiven Projekts* separat aussteht) – ein Sonderfall weniger.
- **`_build_project_graph()` als eigene, reine DB-Aufbaufunktion** getrennt
  von `import_project()` (ZIP-Handling/Validierung/Cleanup): fängt
  `KeyError`/`TypeError`/`ValueError` gebündelt in eine verständliche
  `ValidationAppError` um, statt dass eine unerwartete `data.json`-Struktur
  (z. B. ein manuell frisiertes Archiv) als roher 500er durchschlägt – ein
  gültiges Manifest allein ist keine Garantie für eine wohlgeformte Datei.
- **Datei-Kopien werden bei einem fehlgeschlagenen Import wieder entfernt**
  (`shutil.rmtree` auf das neue Projekt-Upload-Verzeichnis im
  Fehlerpfad von `import_project()`): die DB-Transaktion wird zwar per
  `db.rollback()` zurückgerollt, doch bereits auf die Platte kopierte
  Originaldateien liegen aus Sicht der DB-Transaktion "daneben" und müssen
  deshalb explizit mit aufgeräumt werden, sonst blieben verwaiste Dateien
  ohne zugehörige DB-Zeile zurück.
- **Quellen-Snapshots im exportierten Chatverlauf werden beim Import
  mitremappt** (`quellen[].document_id` wird über dieselbe Document-ID-Map
  wie alle anderen Referenzen umgeschrieben) – sonst würden alte
  Chat-Zitate im importierten Projekt fälschlich als "Quelle gelöscht"
  erscheinen, obwohl das referenzierte Dokument im neuen Projekt genauso
  existiert, nur unter einer neuen ID.
- **Export/Import bewusst ohne API-Key/globale Settings** (siehe Briefing:
  strikte Trennung von System-Backup und Projekt-Export) – ein importiertes
  Projekt nutzt automatisch die auf der Zielinstanz bereits konfigurierte
  Claude-Einstellung, ohne dass der Import selbst eine mitbringt.
- **Backup als eigenständiges Skript (`backend/scripts/backup.py`), nicht als
  API-Endpunkt** – Backups sind eine Infrastruktur-/Betriebsaufgabe (Cron,
  `update.sh`), keine Nutzerfunktion innerhalb der App; ein Endpunkt dafür
  hätte zusätzliche Auth-/Abuse-Überlegungen für eine potenziell
  langlaufende, IO-intensive Operation gebraucht, ohne dass die Instanz
  einen legitimen Deployment-Prozess damit besser bedienen könnte.
- **SQLite-Backup über eine eigene, kurzlebige `sqlite3`-Verbindung statt der
  laufenden SQLAlchemy-Engine** (`backup_service.create_backup`) – `VACUUM
  INTO` soll unabhängig vom Transaktionszustand einer request-gebundenen
  ORM-Session laufen; das Skript ist bewusst als eigenständiger Prozess
  konzipiert (auch per Cron unabhängig vom laufenden App-Prozess aufrufbar),
  nicht als etwas, das sich eine bestehende Datenbankverbindung teilt.
- **Zeitstempel mit Mikrosekunden-Präzision** (`%Y%m%d-%H%M%S-%f`) statt nur
  Sekunden für Backup-Dateinamen – bei zwei Backups innerhalb derselben
  Sekunde (z. B. in Tests, oder falls ein Cron-Backup mit einem manuellen
  überlappt) hätte eine reine Sekunden-Auflösung sonst ein Backup lautlos
  überschrieben.
- **Aufbewahrung der letzten 10 Backups** als fester Default (kein
  Settings-Feld dafür) – im Briefing nur als "einfache
  Aufbewahrungsstrategie" gefordert, ohne konkrete Zahl; als Parameter der
  Funktion (nicht hart einprogrammiert) trotzdem leicht änderbar, falls
  später doch ein Settings-Feld gewünscht wird.
- **Docker Compose: drei Container (Backend, Frontend, Caddy)**, exakt wie im
  Briefing beschrieben, statt Frontend/Reverse-Proxy zu einem Container
  zusammenzulegen – Caddy dient ausschließlich als TLS-Terminierung +
  Basic-Auth + Pfad-Routing, kennt weder Backend noch Frontend im Detail;
  das statisch gebaute Frontend-Image bräuchte sonst zusätzlich eine
  Reverse-Proxy-Konfiguration, die es beim aktuellen Aufbau gar nicht kennen
  muss.
- **Migration läuft nie automatisch im Container-Start-Befehl**, sondern
  ausschließlich als expliziter `docker compose run --rm backend alembic
  upgrade head`-Schritt in `scripts/update.sh`, VOR `docker compose up -d`
  (siehe Briefing: "kontrolliert genau einmal ausführen, nicht parallel aus
  mehreren Workern/Containern heraus" – ein Migrations-Schritt im
  CMD/Entrypoint liefe sonst bei jedem Container-(Neu-)Start erneut, auch bei
  z. B. einem Crash-Restart durch `restart: unless-stopped`).
- **`.gitattributes` erzwingt LF-Zeilenenden** für Shell-Skripte,
  `Dockerfile`, `Caddyfile`, `docker-compose.yml` – diese Dateien landen per
  `git pull` direkt auf dem Linux-VPS; CRLF durch einen Windows-Checkout
  würde das Shebang eines Shell-Skripts unbrauchbar machen ("bad
  interpreter").
- **`SETTINGS_ENCRYPTION_KEY` als Pflichtvariable in `docker-compose.yml`**
  (`${SETTINGS_ENCRYPTION_KEY:?...}`, Compose bricht ohne gesetzten Wert
  kontrolliert mit einer verständlichen Meldung ab) – ein Prod-Start ganz
  ohne dieses Secret wäre zwar laut Briefing tolerierbar (App startet
  trotzdem), in der Docker-Erststart-Situation ist ein sofortiger, klarer
  Abbruch aber hilfreicher als ein später erst bemerktes "Key kann nicht
  gespeichert werden".
- **Beim Schreiben der Restore-Anleitung aufgefallen und korrigiert:** der
  Button "Neu indexieren" pro Dokument (siehe Briefing Punkt 6) war bisher
  nur als "Erneut verarbeiten" bei `status=failed` sichtbar, nicht generell
  verfügbar. Jetzt zusätzlich für `status=ready` sichtbar (nutzt denselben
  bereits vorhandenen `/reprocess`-Endpunkt) – u. a. relevant, falls nach
  einem Restore nur die SQLite-DB, aber nicht der Chroma-Ordner
  zurückgesichert wurde (siehe Backup & Restore oben).
- **Chat-Quellen-Vorschau lädt das Dokument erst bei Klick, nicht vorab**
  (`ChatSection.tsx`, `documentCache` pro Dokument-ID) – bei Konversationen
  mit vielen Quellen würde ein Vorab-Laden aller referenzierten Dokumente
  unnötige Requests erzeugen, obwohl die meisten Quellen nie aufgeklappt
  werden.
- **Spracheingabe als eigener Hook (`hooks/useSpeechDictation.ts`)** statt
  einer neuen Abhängigkeit für serverseitige Transkription – die Web Speech
  API ist bereits im Browser vorhanden (kein neues Package, keine neuen
  Kosten/Latenz durch einen zusätzlichen Dienst), erkannter Text wird an den
  bestehenden Inhalt angehängt statt ihn zu ersetzen (mehrere Diktier-
  Durchgänge möglich). Feature-Detection blendet den Button aus, wenn der
  Browser die API nicht unterstützt, statt einen kaputten Button zu zeigen.
- **`ModelPricing` ohne Projektbezug** (analog zum Claude-API-Key/-Modell,
  siehe Briefing: globale statt projektbezogene Einstellung) – Preise gelten
  instanzweit für alle Projekte gemeinsam.
- **Kostenberechnung holt volle `ApiUsageLog`-Zeilen statt einer SQL-Aggregation**
  (`settings_service.get_usage_summary`) – jede Zeile braucht ihr eigenes,
  zeitpunktabhängiges Preis-Matching (`pricing_service._find_applicable_price`),
  das sich nicht sauber in eine einzelne SQL-Aggregatfunktion pressen lässt;
  bei einer Single-User-Instanz ist das Datenvolumen dafür unproblematisch
  klein. heute/woche sind Teilmengen der Monats-Abfrage, daher genügt ein
  Query für alle drei Zeiträume.

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
