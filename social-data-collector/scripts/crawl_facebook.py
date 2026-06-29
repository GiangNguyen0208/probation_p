"""Standalone script to crawl Facebook Pages against the live Graph API.

By default this script upserts the normalized subject and appends an
activity snapshot to the database (via `sync_subject`, which does both
in a single transaction). Pass --no-persist to skip the DB writes
and just print the raw and normalized responses.

When multiple page IDs are available (via --page-id, FACEBOOK_TEST_PAGE_ID,
or FACEBOOK_TEST_PAGE_IDS), the script crawls each one in turn and
continues on per-page failure so a single bad page doesn't abort the run.

Usage:
    # Use FACEBOOK_TEST_PAGE_ID from .env
    python scripts/crawl_facebook.py --pretty

    # Specify a Page ID explicitly (default behavior persists to DB)
    python scripts/crawl_facebook.py --page-id 1234567890 --pretty

    # Crawl every page in FACEBOOK_TEST_PAGE_IDS, persist each
    python scripts/crawl_facebook.py

    # Just print, don't persist
    python scripts/crawl_facebook.py --page-id 1234567890 --no-persist
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Make the package importable when running this script from any working
# directory, without requiring an editable install.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from social_data_collector.clients.base import RetryPolicy  # noqa: E402
from social_data_collector.clients.facebook import FacebookClient  # noqa: E402
from social_data_collector.config import get_settings  # noqa: E402
from social_data_collector.normalizers.facebook import FacebookNormalizer  # noqa: E402
from social_data_collector.persistence.repository import (  # noqa: E402
    run_in_transaction,
    sync_subject,
)


def _resolve_page_ids(args: argparse.Namespace) -> list[str]:
    """Return the list of page IDs to crawl.

    Priority: explicit --page-id > FACEBOOK_TEST_PAGE_ID > FACEBOOK_TEST_PAGE_IDS.
    """
    if args.page_id:
        return [args.page_id]
    settings = get_settings()
    if settings.facebook.test_page_id:
        return [settings.facebook.test_page_id]
    if settings.facebook.test_page_ids:
        return list(settings.facebook.test_page_ids)
    print(
        "ERROR: No page_id provided and FACEBOOK_TEST_PAGE_ID(S) is empty.",
        file=sys.stderr,
    )
    sys.exit(2)


def _crawl_one(
    page_id: str,
    posts_limit: int,
    retry_policy: RetryPolicy,
) -> tuple[dict, list, object, datetime]:
    """Crawl a single page; return (raw_page, recent_posts, subject, synced_at)."""
    synced_at = datetime.now(UTC)
    settings = get_settings()
    with FacebookClient(settings.facebook, retry_policy) as client:
        raw_page = client.get_page(page_id)
        recent_posts = client.get_recent_posts(page_id, limit=posts_limit)
    subject = FacebookNormalizer().normalize(
        platform_id=page_id,
        raw_response=raw_page,
        activity_data=recent_posts,
        synced_at=synced_at,
    )
    return raw_page, recent_posts, subject, synced_at


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crawl one or more Facebook Pages against the live Graph API."
    )
    parser.add_argument(
        "--page-id",
        help="Facebook Page ID. Defaults to FACEBOOK_TEST_PAGE_ID(S).",
    )
    parser.add_argument(
        "--posts-limit",
        type=int,
        default=10,
        help="Number of recent posts to fetch (default: 10).",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Skip writing to the database (default: persist).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    args = parser.parse_args()

    settings = get_settings()
    if not settings.facebook.has_credentials:
        print(
            "ERROR: Facebook credentials are not configured. "
            "Set FACEBOOK_PAGE_ACCESS_TOKEN or FACEBOOK_APP_ACCESS_TOKEN.",
            file=sys.stderr,
        )
        return 1

    page_ids = _resolve_page_ids(args)
    retry_policy = RetryPolicy(max_attempts=3, initial_seconds=2, max_seconds=30)
    persist = not args.no_persist
    indent = 2 if args.pretty else None

    print(
        f"==> Will crawl {len(page_ids)} page(s) via Graph API "
        f"v{settings.facebook.graph_api_version}, persist={persist}"
    )

    failed: list[tuple[str, str]] = []

    for page_id in page_ids:
        print(f"\n========== {page_id} ==========")
        try:
            raw_page, recent_posts, subject, synced_at = _crawl_one(
                page_id=page_id,
                posts_limit=args.posts_limit,
                retry_policy=retry_policy,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"!!! Crawl failed for {page_id}: {exc}", file=sys.stderr)
            failed.append((page_id, f"crawl: {exc}"))
            continue

        print(f"\n--- {page_id} raw page response ---")
        print(json.dumps(raw_page, indent=indent, default=str))
        print(f"\n--- {len(recent_posts)} recent posts ---")
        print(json.dumps(recent_posts, indent=indent, default=str))
        print(f"\n--- {page_id} normalized Subject ---")
        print(subject.model_dump_json(indent=indent))

        if not persist:
            continue

        try:
            subject_id = run_in_transaction(lambda s, subj=subject: sync_subject(s, subj))
            print(
                f"\n==> Persisted subject_id={subject_id} with snapshot "
                f"captured_at={synced_at.isoformat()}"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"!!! Persist failed for {page_id}: {exc}", file=sys.stderr)
            failed.append((page_id, f"persist: {exc}"))

    if failed:
        print(
            f"\n{len(failed)} of {len(page_ids)} page(s) failed:",
            file=sys.stderr,
        )
        for pid, err in failed:
            print(f"  - {pid}: {err}", file=sys.stderr)
        return 1
    print(f"\n==> Done. {len(page_ids)} page(s) processed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
