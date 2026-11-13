from __future__ import annotations

import os

os.environ.setdefault("CHATBOT_PROVIDER", "mock")
os.environ["ORDER_STORE"] = "memory"
os.environ["MOCK_GENERATION_SECONDS"] = "0"

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.orders.service import reset_order_service


@pytest.fixture(autouse=True)
def _clear_settings_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    reset_order_service()
    yield
    get_settings.cache_clear()
    reset_order_service()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
