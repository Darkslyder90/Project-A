from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import sessionmaker


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    # SQLite hat FK-Constraints standardmaessig deaktiviert - fuer die im Briefing
    # geforderte referenzielle Integritaet (z. B. ON DELETE CASCADE/SET NULL) muss
    # das pro Connection explizit angeschaltet werden.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_engine_and_session_factory(database_url: str) -> tuple[Engine, sessionmaker]:
    """Erzeugt Engine + Sessionmaker ohne Modul-globalen State, damit Tests (und
    ggf. spaeter mehrere Prozesse) jeweils eigene, isolierte Instanzen bekommen
    koennen, statt sich einen Import-Zeit-Singleton zu teilen.
    """
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, session_factory
