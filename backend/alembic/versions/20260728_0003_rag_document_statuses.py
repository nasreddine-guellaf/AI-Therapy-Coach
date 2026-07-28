"""Align document statuses with the RAG ingestion lifecycle.

Revision ID: 20260728_0003
Revises: 20260721_0002
Create Date: 2026-07-28
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260728_0003"
down_revision: str | None = "20260721_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_documents_valid_status"), "documents", type_="check"
    )
    op.execute("UPDATE documents SET status = 'uploaded' WHERE status = 'pending'")
    op.execute("UPDATE documents SET status = 'indexed' WHERE status = 'ready'")
    op.create_check_constraint(
        op.f("ck_documents_valid_status"),
        "documents",
        "status IN ('uploaded', 'processing', 'indexed', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_documents_valid_status"), "documents", type_="check"
    )
    op.execute("UPDATE documents SET status = 'pending' WHERE status = 'uploaded'")
    op.execute("UPDATE documents SET status = 'ready' WHERE status = 'indexed'")
    op.create_check_constraint(
        op.f("ck_documents_valid_status"),
        "documents",
        "status IN ('pending', 'processing', 'ready', 'failed')",
    )
