"""add telegram_users.role column

Revision ID: 0002
Revises: da7dc61cab6e
Create Date: 2026-06-30 11:30:00.000000

Adds a ``role`` column (user_role_enum: 'user' | 'admin') to the
``telegram_users`` table. Existing rows default to ``'user'``.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "da7dc61cab6e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    user_role_enum = sa.Enum("user", "admin", name="user_role_enum")
    user_role_enum.create(op.get_bind())
    op.add_column(
        "telegram_users",
        sa.Column(
            "role",
            user_role_enum,
            nullable=False,
            server_default="user",
        ),
    )


def downgrade() -> None:
    op.drop_column("telegram_users", "role")
    sa.Enum(name="user_role_enum").drop(op.get_bind())
