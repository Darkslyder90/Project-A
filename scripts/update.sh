#!/usr/bin/env bash
set -euo pipefail

# Project-A Update-Skript (siehe PROJECT_BRIEFING.md, Abschnitt "Updates,
# Migrationen, Backup & Healthcheck"). Reihenfolge ist bewusst fest:
#   1. Backup erstellen
#   2. neuen Code holen (git pull)
#   3. Images bauen
#   4. Migration kontrolliert genau einmal ausfuehren
#   5. Anwendung (neu) starten
#   6. Healthcheck pruefen
#
# Schlaegt Schritt 4 (Migration) fehl, bricht das Skript sofort ab (set -e) -
# "docker compose up" (Schritt 5) wird dann NIE erreicht, die zuvor laufende
# Anwendung bleibt unangetastet weiterlaufen. Ein fehlgeschlagener Healthcheck
# am Ende (Schritt 6) wird laut, aber die neue Anwendung laeuft zu diesem
# Zeitpunkt bereits - das Skript kann keine automatische Rueckabwicklung des
# Deployments selbst vornehmen, macht das Problem aber sofort sichtbar.

cd "$(dirname "$0")/.."

echo "==> 1/6 Backup erstellen"
docker compose run --rm backend python -m scripts.backup

echo "==> 2/6 Neuen Code holen"
git pull --ff-only

echo "==> 3/6 Images bauen"
docker compose build

echo "==> 4/6 Migration ausfuehren (einmalig, kontrolliert - siehe Briefing)"
docker compose run --rm backend alembic upgrade head

echo "==> 5/6 Anwendung starten/aktualisieren"
docker compose up -d

echo "==> 6/6 Healthcheck pruefen"
for _ in $(seq 1 15); do
    if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
        echo "Healthcheck OK - Update abgeschlossen."
        exit 0
    fi
    sleep 2
done

echo "FEHLER: Healthcheck nach dem Update war nicht innerhalb von 30s erfolgreich." >&2
echo "Die Anwendung wurde bereits gestartet - bitte 'docker compose logs backend' pruefen." >&2
exit 1
