import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

# Anzahl automatischer Backups, die aufbewahrt werden (siehe Briefing: "einfache
# Aufbewahrungsstrategie ... damit nicht unbegrenzt Backups anwachsen").
DEFAULT_RETENTION = 10

_ARCHIVE_PREFIX = "project-a-backup-"


def create_backup(
    *, database_path: Path, data_dir: Path, backups_dir: Path, retention: int = DEFAULT_RETENTION
) -> Path:
    """Erstellt ein konsistentes Backup von SQLite-DB + Uploads (siehe Briefing:
    Backup-Abschnitt). Chroma wird bewusst NICHT gesichert (abgeleitete,
    jederzeit aus SQLite + Originaldateien rekonstruierbare Indexdaten, siehe
    Source-of-Truth-Prinzip). Das SETTINGS_ENCRYPTION_KEY-Secret ist ebenfalls
    NICHT Teil dieses Backups, da es ausschliesslich in der Prozessumgebung/
    .env liegt, nie in der SQLite-DB - es muss separat aufbewahrt werden
    (siehe README "Encryption-Secret").

    Die SQLite-Sicherung laeuft ueber `VACUUM INTO` statt eines rohen
    Datei-Kopiervorgangs, damit das Backup auch bei einer parallel
    schreibenden Anwendung garantiert konsistent ist. Dieses Skript oeffnet
    dafuer eine eigene, kurzlebige sqlite3-Verbindung - unabhaengig vom
    laufenden Anwendungsprozess/dessen SQLAlchemy-Engine.
    """
    backups_dir.mkdir(parents=True, exist_ok=True)
    # Mikrosekunden-Praezision statt nur Sekunden: verhindert Dateinamens-
    # Kollisionen, wenn kurz hintereinander mehrere Backups erstellt werden
    # (z. B. in Tests oder falls ein Cron-Backup mit einem Update ueberlappt).
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    work_dir = backups_dir / f"_tmp-{timestamp}"
    work_dir.mkdir(parents=True)

    try:
        db_backup_path = work_dir / "project-a.db"
        connection = sqlite3.connect(str(database_path))
        try:
            connection.execute("VACUUM INTO ?", (str(db_backup_path),))
        finally:
            connection.close()

        uploads_dir = data_dir / "uploads"
        if uploads_dir.is_dir():
            shutil.copytree(uploads_dir, work_dir / "uploads")

        archive_base = backups_dir / f"{_ARCHIVE_PREFIX}{timestamp}"
        archive_path = Path(shutil.make_archive(str(archive_base), "zip", root_dir=work_dir))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    _apply_retention(backups_dir, retention)
    return archive_path


def _apply_retention(backups_dir: Path, retention: int) -> None:
    if retention <= 0:
        return
    backups = list_backups(backups_dir)
    # list_backups sortiert neueste zuerst - die aeltesten ueber dem Limit entfernen.
    for old_backup in backups[retention:]:
        old_backup.unlink(missing_ok=True)


def list_backups(backups_dir: Path) -> list[Path]:
    return sorted(backups_dir.glob(f"{_ARCHIVE_PREFIX}*.zip"), reverse=True)
