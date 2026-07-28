from fastapi.testclient import TestClient

from app.main import app

def test_health() -> None:
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "AI Therapy Coach Backend",
    }


def test_application_startup_does_not_create_or_modify_database_schema() -> None:
    """Schema ownership belongs exclusively to Alembic migrations."""
    import app.main as main_module

    assert not hasattr(main_module, "initialize_database")
