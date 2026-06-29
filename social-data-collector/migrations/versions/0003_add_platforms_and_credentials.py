"""add platforms + platform_credentials tables + credential_id on subjects

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-26 12:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- platforms ---
    op.create_table(
        "platforms",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("auth_type", sa.String(length=50), nullable=False),
        sa.Column("config_schema", postgresql.JSONB(), nullable=False),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_platforms_slug"), "platforms", ["slug"], unique=True)

    # --- platform_credentials ---
    op.create_table(
        "platform_credentials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("platform_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("credentials", postgresql.JSONB(), nullable=False),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default=sa.text("'active'")
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["platform_id"], ["platforms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_platform_credentials_platform_id"),
        "platform_credentials",
        ["platform_id"],
        unique=False,
    )

    # --- credential_id on subjects ---
    op.add_column(
        "subjects",
        sa.Column(
            "credential_id",
            sa.UUID(),
            nullable=True,
        ),
    )
    op.create_unique_constraint("uq_subjects_credential_id", "subjects", ["credential_id"])
    op.create_foreign_key(
        "fk_subjects_credential_id",
        "subjects",
        "platform_credentials",
        ["credential_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- seed default platforms ---
    op.execute(
        sa.text(
            """
            INSERT INTO platforms (id, name, slug, auth_type, config_schema, is_active)
            VALUES
            (
                gen_random_uuid(),
                'Facebook',
                'facebook',
                'access_token',
                '{"access_token": {"type": "string", "label": "Page Access Token", "required": true, "sensitive": true}, "page_id": {"type": "string", "label": "Facebook Page ID", "required": true, "sensitive": false}, "app_id": {"type": "string", "label": "Facebook App ID", "required": false, "sensitive": false}, "app_secret": {"type": "string", "label": "Facebook App Secret", "required": false, "sensitive": true}}'::jsonb,
                true
            ),
            (
                gen_random_uuid(),
                'YouTube',
                'youtube',
                'api_key',
                '{"api_key": {"type": "string", "label": "YouTube API Key", "required": true, "sensitive": true}, "channel_id": {"type": "string", "label": "YouTube Channel ID", "required": true, "sensitive": false}}'::jsonb,
                true
            )
            """
        ),
    )


def downgrade() -> None:
    op.drop_constraint("fk_subjects_credential_id", "subjects", type_="foreignkey")
    op.drop_constraint("uq_subjects_credential_id", "subjects", type_="unique")
    op.drop_column("subjects", "credential_id")
    op.drop_index(
        op.f("ix_platform_credentials_platform_id"),
        table_name="platform_credentials",
    )
    op.drop_table("platform_credentials")
    op.drop_index(op.f("ix_platforms_slug"), table_name="platforms")
    op.drop_table("platforms")
