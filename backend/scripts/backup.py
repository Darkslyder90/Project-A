"""Eigenstaendiges Backup-Skript (siehe Briefing: Backup vor jedem Update,
siehe scripts/update.sh im Repo-Root). Nutzt dieselbe Settings-Konfiguration
wie die laufende App (DATA_DIR etc. aus der Umgebung/.env), laeuft aber
unabhaengig vom laufenden Server-Prozess - kann daher auch per Cron
periodisch aufgerufen werden, nicht nur im Rahmen eines Updates.

Aufruf (aus backend/, mit aktivierter venv bzw. im Docker-Container):
    python -m scripts.backup
"""

from app.config import get_settings
from app.services.backup_service import create_backup


def main() -> None:
    settings = get_settings()
    settings.ensure_persistent_dirs()
    archive_path = create_backup(
        database_path=settings.database_path,
        data_dir=settings.data_dir,
        backups_dir=settings.backups_dir,
    )
    print(f"Backup erstellt: {archive_path}")


if __name__ == "__main__":
    main()
