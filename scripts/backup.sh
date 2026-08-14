#!/usr/bin/env bash
set -euo pipefail

# Eigenstaendiger Backup-Aufruf ausserhalb eines Updates - z. B. fuer einen
# taeglichen Cron-Job (siehe scripts/update.sh fuer den Aufruf als Teil eines
# Updates, dieselbe Logik dahinter siehe backend/app/services/backup_service.py).
#
# Beispiel-Cronjob (taeglich 3 Uhr):
#   0 3 * * * cd /pfad/zu/project-a && ./scripts/backup.sh >> /var/log/project-a-backup.log 2>&1

cd "$(dirname "$0")/.."

docker compose run --rm backend python -m scripts.backup
