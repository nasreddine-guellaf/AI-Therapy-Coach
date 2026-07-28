from sqlalchemy import inspect

from app.infrastructure.database.models import Base


def test_expected_database_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "coaching_sessions",
        "messages",
        "documents",
        "memory_entries",
    }


def test_memory_entry_has_future_retention_fields() -> None:
    columns = {column.name for column in Base.metadata.tables["memory_entries"].columns}
    assert {"user_id", "session_id", "source_message_id", "is_active", "expires_at"} <= columns


def test_user_model_contains_only_hashed_authentication_credentials() -> None:
    table = Base.metadata.tables["users"]
    columns = {column.name for column in table.columns}
    assert {
        "id",
        "email",
        "hashed_password",
        "full_name",
        "is_active",
        "created_at",
        "updated_at",
    } <= columns
    assert "password" not in columns
    assert table.c.email.unique


def test_all_models_have_uuid_primary_keys() -> None:
    for table in Base.metadata.sorted_tables:
        primary_key = inspect(table).primary_key
        assert [column.name for column in primary_key] == ["id"]


def test_conversation_tables_support_titles_and_optional_metadata() -> None:
    sessions = {
        column.name for column in Base.metadata.tables["coaching_sessions"].columns
    }
    messages = {column.name for column in Base.metadata.tables["messages"].columns}
    assert {"id", "user_id", "title", "created_at", "updated_at"} <= sessions
    assert {"id", "session_id", "role", "content", "metadata", "created_at"} <= messages


def test_document_model_supports_rag_ingestion_metadata() -> None:
    columns = {column.name for column in Base.metadata.tables["documents"].columns}
    assert {"user_id", "filename", "content_type", "checksum", "status"} <= columns
    constraints = {
        str(constraint.sqltext)
        for constraint in Base.metadata.tables["documents"].constraints
        if hasattr(constraint, "sqltext")
    }
    assert any("uploaded" in expression and "indexed" in expression for expression in constraints)
