"""Alembic environment for the API gateway.

Loads the DATABASE_URL from the project-root .env and runs migrations
against the same database the application reads from. Only manages
tables owned by the gateway (currently `api_keys`); the collector's
tables are managed by the collector's own Alembic config.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "social-api-gateway" / "src"))

load_dotenv(_PROJECT_ROOT / ".env", override=False)

# Import models so their tables are registered on Base.metadata
from social_api_gateway.auth.models import APIKeyModel  # noqa: E402, F401
from social_api_gateway.config import get_settings  # noqa: E402
from social_api_gateway.db import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database.url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
