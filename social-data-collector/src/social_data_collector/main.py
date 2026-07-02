"""CLI entrypoint for manual sync, seeding, and health checks.

This CLI is the manual counterpart used
for debugging, smoke tests, one-off syncs, and initial subject seeding.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from social_common.enums import Platform, SubjectStatus
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .health import run_health_check
from .logging_setup import configure_logging, get_logger
from .persistence.credential_resolver import encrypt_credentials
from .persistence.models import PlatformCredentialModel, PlatformModel, SubjectModel
from .persistence.repository import run_in_transaction
from .scheduler.tasks import (
    sync_all_facebook_subjects,
    sync_all_tiktok_subjects,
    sync_all_youtube_subjects,
    sync_facebook_subject,
    sync_tiktok_subject,
    sync_youtube_subject,
)


def _make_seeder(platform: Platform, platform_id: str) -> Any:
    """Return a callable that seeds one subject into a session."""

    def _seed(session: Session) -> bool:
        return _seed_one_subject(session, platform, platform_id)

    return _seed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="social-data-collector")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("sync-facebook", help="Sync all configured Facebook subjects once.")
    subparsers.add_parser("sync-youtube", help="Sync all configured YouTube subjects once.")
    subparsers.add_parser("sync-tiktok", help="Sync all configured TikTok subjects once.")
    subparsers.add_parser("sync-all", help="Sync all configured subjects on all platforms once.")
    subparsers.add_parser("health", help="Print health check for DB and Redis.")
    subparsers.add_parser(
        "seed-subjects",
        help="Seed subjects from env-var lists (FACEBOOK_TEST_PAGE_IDS, YOUTUBE_TEST_CHANNEL_IDS) into the DB.",
    )
    subparsers.add_parser(
        "seed-platforms",
        help="Seed the default platforms (Facebook, YouTube, TikTok) into the platforms table.",
    )

    store_cred = subparsers.add_parser(
        "store-credential",
        help="Encrypt and store a credential blob in platform_credentials.",
    )
    store_cred.add_argument("--platform-slug", required=True, help="Platform slug (e.g. tiktok)")
    store_cred.add_argument("--label", required=True, help="Human-readable label")
    store_cred.add_argument(
        "--data", required=True, help='JSON object with credential fields (e.g. {"access_token":"..."})'
    )

    fb_one = subparsers.add_parser("sync-facebook-one", help="Sync a single Facebook Page by ID.")
    fb_one.add_argument("page_id")

    yt_one = subparsers.add_parser("sync-youtube-one", help="Sync a single YouTube channel by ID.")
    yt_one.add_argument("channel_id")

    tt_one = subparsers.add_parser("sync-tiktok-one", help="Sync a single TikTok user by open_id.")
    tt_one.add_argument("open_id")

    return parser


def _handle_health(logger: structlog.stdlib.BoundLogger) -> int:
    result = run_health_check()
    print(json.dumps(result, indent=2, default=str))
    if result["status"] != "ok":
        logger.error("health.check.failed", **result)
        return 1
    logger.info("health.check.ok", **result)
    return 0


def _seed_one_subject(
    session: Session,
    platform: Platform,
    platform_id: str,
) -> bool:
    """Insert a placeholder subject if it doesn't already exist.

    Returns True if a new row was inserted, False if it already existed.
    The first sync will fill in the real name/followers/etc from the API.
    """
    existing = session.execute(
        select(SubjectModel).where(
            SubjectModel.platform == platform,
            SubjectModel.platform_id == platform_id,
        )
    ).scalar_one_or_none()
    if existing:
        return False

    session.add(
        SubjectModel(
            platform=platform,
            platform_id=platform_id,
            name=f"Pending sync: {platform_id}",
            display_name=f"Pending sync: {platform_id}",
            followers=0,
            post_count=0,
            activity_frequency=0.0,
            status=SubjectStatus.INACTIVE,
            last_synced_at=datetime.now(UTC),
        )
    )
    session.commit()
    return True


def _handle_seed_platforms(logger: structlog.stdlib.BoundLogger) -> int:
    """Seed default platforms (Facebook, YouTube) into the platforms table.

    Idempotent: platforms already in the DB are not duplicated.
    """
    default_platforms = [
        {
            "name": "Facebook",
            "slug": "facebook",
            "auth_type": "access_token",
            "config_schema": {
                "access_token": {
                    "type": "string",
                    "label": "Page Access Token",
                    "required": True,
                    "sensitive": True,
                },
                "page_id": {
                    "type": "string",
                    "label": "Facebook Page ID",
                    "required": True,
                    "sensitive": False,
                },
                "app_id": {
                    "type": "string",
                    "label": "Facebook App ID",
                    "required": False,
                    "sensitive": False,
                },
                "app_secret": {
                    "type": "string",
                    "label": "Facebook App Secret",
                    "required": False,
                    "sensitive": True,
                },
            },
        },
        {
            "name": "YouTube",
            "slug": "youtube",
            "auth_type": "api_key",
            "config_schema": {
                "api_key": {
                    "type": "string",
                    "label": "YouTube API Key",
                    "required": True,
                    "sensitive": True,
                },
                "channel_id": {
                    "type": "string",
                    "label": "YouTube Channel ID",
                    "required": True,
                    "sensitive": False,
                },
            },
        },
        {
            "name": "TikTok",
            "slug": "tiktok",
            "auth_type": "oauth2",
            "config_schema": {
                "access_token": {
                    "type": "string",
                    "label": "TikTok Access Token",
                    "required": True,
                    "sensitive": True,
                },
                "refresh_token": {
                    "type": "string",
                    "label": "TikTok Refresh Token",
                    "required": False,
                    "sensitive": True,
                },
                "client_key": {
                    "type": "string",
                    "label": "TikTok Client Key",
                    "required": False,
                    "sensitive": False,
                },
                "client_secret": {
                    "type": "string",
                    "label": "TikTok Client Secret",
                    "required": False,
                    "sensitive": True,
                },
            },
        },
    ]

    def _make_platform_seeder(data: dict[str, Any]) -> Callable[[Session], bool]:
        slug = data["slug"]

        def _seed_platform(session: Session) -> bool:
            existing = session.execute(
                select(PlatformModel).where(PlatformModel.slug == slug)
            ).scalar_one_or_none()
            if existing:
                return False
            session.add(
                PlatformModel(
                    id=uuid4(),
                    name=data["name"],
                    slug=slug,
                    auth_type=data["auth_type"],
                    config_schema=data["config_schema"],
                    is_active=True,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
            session.commit()
            return True

        return _seed_platform

    seeded = 0
    for platform_data in default_platforms:
        inserted = run_in_transaction(_make_platform_seeder(platform_data))
        if inserted:
            seeded += 1
            logger.info("seed.platform", slug=platform_data["slug"], name=platform_data["name"])

    logger.info("seed.platforms.complete", seeded=seeded)
    return 0


def _handle_seed_subjects(logger: structlog.stdlib.BoundLogger) -> int:
    """Seed subjects from env-var lists into the DB.

    Idempotent: subjects already in the DB are not duplicated. Run once
    after migrations to populate the auto-sync target list, or whenever
    new subject IDs are added to the env-var lists.
    """
    settings = get_settings()
    seeded = 0

    for page_id in settings.facebook.test_page_ids:
        inserted = run_in_transaction(_make_seeder(Platform.FACEBOOK, page_id))
        if inserted:
            seeded += 1
            logger.info("seed.subject", platform="facebook", platform_id=page_id)

    for channel_id in settings.youtube.test_channel_ids:
        inserted = run_in_transaction(_make_seeder(Platform.YOUTUBE, channel_id))
        if inserted:
            seeded += 1
            logger.info("seed.subject", platform="youtube", platform_id=channel_id)

    logger.info("seed.complete", seeded=seeded)
    return 0


def _handle_store_credential(
    args: argparse.Namespace,
    logger: structlog.stdlib.BoundLogger,
) -> int:
    """Encrypt and store a credential blob for a platform."""
    try:
        raw_data = json.loads(args.data)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in --data: {exc}", file=sys.stderr)
        return 1

    if not isinstance(raw_data, dict):
        print("--data must be a JSON object", file=sys.stderr)
        return 1

    try:
        encrypted_blob = encrypt_credentials(raw_data)
    except Exception as exc:  # noqa: BLE001
        print(f"Encryption failed: {exc}", file=sys.stderr)
        return 1

    slug = args.platform_slug
    label = args.label

    def _work(session: Session) -> UUID:
        platform = session.execute(
            select(PlatformModel).where(PlatformModel.slug == slug)
        ).scalar_one_or_none()
        if platform is None:
            raise ValueError(f"Platform '{slug}' not found. Run seed-platforms first.")

        cred = PlatformCredentialModel(
            id=uuid4(),
            platform_id=platform.id,
            label=label,
            credentials=encrypted_blob,
            status="active",
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(cred)
        session.commit()
        return cred.id

    try:
        cred_id = run_in_transaction(_work)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Database error: {exc}", file=sys.stderr)
        return 1

    print(f"Credential stored: {cred_id}")
    logger.info("credential.stored", credential_id=str(cred_id), platform_slug=slug, label=label)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    settings = get_settings()
    configure_logging(settings.runtime.log_level)
    logger = get_logger("social_data_collector.main")

    parser = _build_parser()
    args = parser.parse_args(argv)

    command = args.command

    if command == "sync-facebook":
        return sync_all_facebook_subjects()
    if command == "sync-youtube":
        return sync_all_youtube_subjects()
    if command == "sync-tiktok":
        return sync_all_tiktok_subjects()
    if command == "sync-all":
        rc = sync_all_facebook_subjects()
        rc |= sync_all_youtube_subjects()
        rc |= sync_all_tiktok_subjects()
        return rc
    if command == "sync-facebook-one":
        sync_facebook_subject(args.page_id)
        return 0
    if command == "sync-youtube-one":
        sync_youtube_subject(args.channel_id)
        return 0
    if command == "sync-tiktok-one":
        sync_tiktok_subject(args.open_id)
        return 0
    if command == "health":
        return _handle_health(logger)
    if command == "seed-subjects":
        return _handle_seed_subjects(logger)
    if command == "seed-platforms":
        return _handle_seed_platforms(logger)
    if command == "store-credential":
        return _handle_store_credential(args, logger)

    parser.error(f"Unknown command: {command}")
    return 2  # unreachable


if __name__ == "__main__":
    sys.exit(main())
