"""add telegram_users table

Revision ID: da7dc61cab6e
Revises: dc10e5695da0
Create Date: 2026-06-30 10:39:55.131523

The autogenerate detected tables owned by other services (collector,
alert-engine) in the shared DB. Only the ``telegram_users`` table is
managed by this migration — no foreign tables are touched.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "da7dc61cab6e"
down_revision: str | None = "dc10e5695da0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "telegram_users",
        sa.Column("telegram_id", sa.BigInteger(), autoincrement=False, nullable=False, comment="Telegram user ID from initData."),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("last_name", sa.String(length=128), nullable=True),
        sa.Column("username", sa.String(length=128), nullable=True),
        sa.Column("language_code", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("telegram_id"),
    )


def downgrade() -> None:
    op.drop_table("telegram_users")
