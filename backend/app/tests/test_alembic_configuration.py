"""Static checks for migration ownership and Alembic wiring."""

from pathlib import Path

from app.infrastructure.database.models import Base


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_alembic_targets_application_metadata() -> None:
    env_file = (BACKEND_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")
    assert "from app.infrastructure.database.models import Base" in env_file
    assert "target_metadata = Base.metadata" in env_file
    assert (BACKEND_ROOT / "alembic.ini").is_file()


def test_initial_migration_covers_current_schema() -> None:
    migration = (
        BACKEND_ROOT / "alembic" / "versions" / "20260721_0001_initial_schema.py"
    ).read_text(encoding="utf-8")
    for table_name in Base.metadata.tables:
        assert f'"{table_name}"' in migration
    assert 'revision: str = "20260721_0001"' in migration
    assert "down_revision: str | None = None" in migration


def test_history_index_migration_follows_baseline() -> None:
    migration = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260721_0002_history_listing_index.py"
    ).read_text(encoding="utf-8")
    assert 'down_revision: str | None = "20260721_0001"' in migration
    assert "ix_coaching_sessions_user_updated" in migration
