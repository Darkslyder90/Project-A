import sqlite3
import zipfile
from pathlib import Path

from app.services.backup_service import create_backup, list_backups


def _make_sqlite_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT)")
    con.execute("INSERT INTO projects (name) VALUES ('Testprojekt')")
    con.commit()
    con.close()


def test_create_backup_produces_zip_with_db_and_uploads(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    database_path = data_dir / "project-a.db"
    _make_sqlite_db(database_path)

    uploads_dir = data_dir / "uploads" / "1" / "1"
    uploads_dir.mkdir(parents=True)
    (uploads_dir / "original.txt").write_text("Originalinhalt")

    backups_dir = tmp_path / "backups"

    archive_path = create_backup(database_path=database_path, data_dir=data_dir, backups_dir=backups_dir)

    assert archive_path.is_file()
    assert archive_path.suffix == ".zip"

    with zipfile.ZipFile(archive_path) as zf:
        names = zf.namelist()
        assert "project-a.db" in names
        assert any(n.endswith("original.txt") for n in names)

        # Backup-DB ist eigenstaendig lesbar und enthaelt dieselben Daten.
        zf.extract("project-a.db", tmp_path / "extracted")
        con = sqlite3.connect(str(tmp_path / "extracted" / "project-a.db"))
        rows = con.execute("SELECT name FROM projects").fetchall()
        con.close()
        assert rows == [("Testprojekt",)]


def test_create_backup_excludes_chroma_dir(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    database_path = data_dir / "project-a.db"
    _make_sqlite_db(database_path)
    (data_dir / "chroma").mkdir()
    (data_dir / "chroma" / "irrelevant.bin").write_bytes(b"fake-vector-data")

    backups_dir = tmp_path / "backups"
    archive_path = create_backup(database_path=database_path, data_dir=data_dir, backups_dir=backups_dir)

    with zipfile.ZipFile(archive_path) as zf:
        assert not any("chroma" in n for n in zf.namelist())


def test_create_backup_without_uploads_dir_still_succeeds(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    database_path = data_dir / "project-a.db"
    _make_sqlite_db(database_path)

    backups_dir = tmp_path / "backups"
    archive_path = create_backup(database_path=database_path, data_dir=data_dir, backups_dir=backups_dir)

    assert archive_path.is_file()


def test_list_backups_returns_newest_first(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    database_path = data_dir / "project-a.db"
    _make_sqlite_db(database_path)
    backups_dir = tmp_path / "backups"

    first = create_backup(database_path=database_path, data_dir=data_dir, backups_dir=backups_dir)
    second = create_backup(database_path=database_path, data_dir=data_dir, backups_dir=backups_dir)

    backups = list_backups(backups_dir)
    assert backups[0].name >= backups[1].name  # neuester Zeitstempel zuerst
    assert set(backups) == {first, second}


def test_retention_removes_oldest_backups_beyond_limit(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    database_path = data_dir / "project-a.db"
    _make_sqlite_db(database_path)
    backups_dir = tmp_path / "backups"

    created = [
        create_backup(database_path=database_path, data_dir=data_dir, backups_dir=backups_dir, retention=3)
        for _ in range(5)
    ]

    remaining = list_backups(backups_dir)
    assert len(remaining) == 3
    # Die drei zuletzt erstellten Backups muessen uebrig sein.
    assert set(remaining) == set(created[-3:])


def test_retention_zero_keeps_all_backups(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    database_path = data_dir / "project-a.db"
    _make_sqlite_db(database_path)
    backups_dir = tmp_path / "backups"

    for _ in range(3):
        create_backup(database_path=database_path, data_dir=data_dir, backups_dir=backups_dir, retention=0)

    assert len(list_backups(backups_dir)) == 3
