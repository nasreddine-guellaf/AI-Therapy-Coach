import asyncio
import importlib
import logging

from asyncpg import InvalidPasswordError
from fastapi.testclient import TestClient

from app.main import app

def test_health() -> None:
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "AI Therapy Coach Backend",
    }


def test_lifespan_survives_database_driver_failure(monkeypatch, caplog) -> None:
    """A bad database credential must not prevent the liveness API starting."""
    main_module = importlib.import_module("app.main")

    async def fail_initialization() -> None:
        try:
            raise InvalidPasswordError("password=must-never-be-logged")
        except InvalidPasswordError as cause:
            raise OSError("outer-message-must-not-be-logged") from cause

    async def close_without_database() -> None:
        return None

    monkeypatch.setattr(main_module, "initialize_database", fail_initialization)
    monkeypatch.setattr(main_module, "close_database_engine", close_without_database)
    monkeypatch.setattr(main_module.settings, "database_auto_create", True)
    caplog.set_level(logging.WARNING, logger="app.main")

    async def run_lifespan() -> None:
        async with main_module.lifespan(main_module.app):
            pass

    asyncio.run(run_lifespan())

    assert "error_type=OSError" in caplog.text
    assert "cause_type=InvalidPasswordError" in caplog.text
    assert "must-never-be-logged" not in caplog.text
