"""add_alert_logs

Revision ID: 27047c01eaa0
Revises:
Create Date: 2026-06-25 17:48:24.600998

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "27047c01eaa0"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alert_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column("rule_id", sa.UUID(), nullable=True),
        sa.Column(
            "rule_type",
            sa.String(50),
            nullable=False,
        ),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("delivered", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["alert_rules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alert_logs_rule_id"), "alert_logs", ["rule_id"], unique=False)
    op.create_index(op.f("ix_alert_logs_subject_id"), "alert_logs", ["subject_id"], unique=False)
    op.create_index(
        op.f("ix_alert_logs_triggered_at"),
        "alert_logs",
        ["triggered_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_alert_logs_triggered_at"), table_name="alert_logs")
    op.drop_index(op.f("ix_alert_logs_subject_id"), table_name="alert_logs")
    op.drop_index(op.f("ix_alert_logs_rule_id"), table_name="alert_logs")
    op.drop_table("alert_logs")
