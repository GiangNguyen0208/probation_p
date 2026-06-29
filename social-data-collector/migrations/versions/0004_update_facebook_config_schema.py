"""update facebook platform config_schema with app_id and app_secret

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-29 12:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE platforms
        SET config_schema = config_schema || '{
          "app_id": {"type": "string", "label": "Facebook App ID", "required": false, "sensitive": false},
          "app_secret": {"type": "string", "label": "Facebook App Secret", "required": false, "sensitive": true}
        }'::jsonb
        WHERE slug = 'facebook'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE platforms
        SET config_schema = config_schema - 'app_id' - 'app_secret'
        WHERE slug = 'facebook'
        """
    )
