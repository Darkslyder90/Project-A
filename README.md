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

Alle weiteren Schritte (Retrieval-Test, Chat, persistente Konversationen,
Datei-Upload, Bildanalyse, Personen/Tasks/Meetings, Übersichtsseiten, Settings,
Export/Import, Backup/Update, Docker/Prod-Deployment) folgen schrittweise.

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
