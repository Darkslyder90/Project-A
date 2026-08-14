from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-Root = zwei Ebenen ueber diesem File (backend/app/config.py -> backend/ -> Repo-Root)
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # "dev" oder "prod" - steuert nur den Default von data_dir, keine sonstige Logik
    env: str = "dev"

    # Basisverzeichnis fuer alle persistenten Nutzdaten (siehe Briefing: Persistenzpfade).
    # Muss unabhaengig vom aktuellen Arbeitsverzeichnis funktionieren, daher Default relativ
    # zum Repo-Root statt zu cwd. In Prod wird das per .env auf /data gesetzt (Docker-Volume).
    data_dir: Path = _REPO_ROOT / "data-dev"

    # Optionaler Override, falls die DB nicht unter data_dir/project-a.db liegen soll.
    database_url: str | None = None

    # Fernet-Key zur Verschluesselung des in SQLite gespeicherten Claude-API-Keys.
    # Bewusst NICHT in der DB, siehe Briefing "Encryption-Secret explizit ausgenommen".
    # Fehlt er, startet die App trotzdem (Claude-Ausfall darf App nicht lahmlegen) -
    # nur Verschluesselung/Entschluesselung eines gespeicherten Keys schlaegt dann fehl.
    settings_encryption_key: str | None = None

    # Optionaler Fallback-Claude-Key, falls in der DB keiner hinterlegt ist.
    claude_api_key: str | None = None

    max_upload_size_mb: int = 50

    # Kommagetrennte Liste erlaubter Frontend-Origins (Dev: Vite-Dev-Server).
    cors_origins: str = "http://localhost:5173"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "project-a.db"

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.database_path.as_posix()}"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def embedding_model_cache_dir(self) -> Path:
        return self.data_dir / "embedding-model-cache"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_persistent_dirs(self) -> None:
        for path in (
            self.data_dir,
            self.uploads_dir,
            self.chroma_dir,
            self.embedding_model_cache_dir,
            self.backups_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
