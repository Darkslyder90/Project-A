from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import models  # noqa: F401  (registriert alle Modelle bei Base.metadata)
from app.db.base import Base
from app.main import create_app


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", env="test")


@pytest.fixture
def app(test_settings: Settings):
    application = create_app(test_settings)
    Base.metadata.create_all(bind=application.state.engine)
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c
