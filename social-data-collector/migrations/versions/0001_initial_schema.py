"""initial schema with TimescaleDB hypertable

Revision ID: 0001
Revises:
Create Date: 2026-06-19 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable the TimescaleDB extension. The image bundled in docker-compose
    # already has the extension installed, but CREATE EXTENSION is
    # idempotent and safe to call.
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    op.create_table(
        "subjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "platform",
            sa.Enum(
                "facebook",
                "youtube",
                name="platform_enum",
            ),
            nullable=False,
        ),
        sa.Column("platform_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("display_name", sa.String(length=500), nullable=False),
        sa.Column("followers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("post_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("activity_frequency", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", "suspended", name="subject_status_enum"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("platform", "platform_id", name="uq_subjects_platform_platform_id"),
    )
    op.create_index("ix_subjects_platform", "subjects", ["platform"])
    op.create_index("ix_subjects_platform_id", "subjects", ["platform_id"])

    op.create_table(
        "activity_snapshots",
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("followers", sa.Integer(), nullable=False),
        sa.Column("post_count", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("subject_id", "captured_at", name="pk_activity_snapshots"),
    )
    op.create_index(
        "ix_activity_snapshots_captured_at",
        "activity_snapshots",
        ["captured_at"],
    )

    # Convert activity_snapshots to a TimescaleDB hypertable partitioned
    # on captured_at. This is the time-series store referenced in the
    # architecture document.
    op.execute(
        "SELECT create_hypertable('activity_snapshots', 'captured_at', "
        "chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE)"
    )

    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "rule_type",
            sa.Enum(
                "follower_spike",
                "follower_drop",
                "activity_spike",
                "activity_silence",
                "status_change",
                name="alert_rule_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_alert_rules_subject_id", "alert_rules", ["subject_id"])


def downgrade() -> None:
    op.drop_index("ix_alert_rules_subject_id", table_name="alert_rules")
    op.drop_table("alert_rules")

    # Hypertable must be dropped (or converted back) before the underlying
    # table can be dropped. TimescaleDB handles this automatically when
    # the table is dropped, but we drop the hypertable explicitly for
    # clarity.
    op.execute("SELECT 1")  # placeholder; drop_table below handles cleanup
    op.drop_index("ix_activity_snapshots_captured_at", table_name="activity_snapshots")
    op.drop_table("activity_snapshots")

    op.drop_index("ix_subjects_platform_id", table_name="subjects")
    op.drop_index("ix_subjects_platform", table_name="subjects")
    op.drop_table("subjects")

    op.execute("DROP TYPE IF EXISTS alert_rule_type_enum")
    op.execute("DROP TYPE IF EXISTS subject_status_enum")
    op.execute("DROP TYPE IF EXISTS platform_enum")
