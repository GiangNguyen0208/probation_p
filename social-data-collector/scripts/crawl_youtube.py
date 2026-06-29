"""Standalone script to crawl YouTube Channels against the live Data API v3.

By default this script upserts the normalized subject and appends an
activity snapshot to the database (via `sync_subject`, which does both
in a single transaction). Pass --no-persist to skip the DB writes
and just print the raw and normalized responses.

When multiple channel IDs are available (via --channel-id,
YOUTUBE_TEST_CHANNEL_ID, or YOUTUBE_TEST_CHANNEL_IDS), the script
crawls each one in turn and continues on per-channel failure so a
single bad channel doesn't abort the run.

Quota cost per channel: 2 units minimum
  - channels.list        → 1 unit
  - playlistItems.list   → 1 unit per page (default: 1 page = 50 items)

With the default 10,000 units/day quota and 60-minute sync interval,
this safely supports ~4,800 channels/day.

Usage:
    # Use YOUTUBE_TEST_CHANNEL_ID from .env
    python scripts/crawl_youtube.py --pretty

    # Specify a Channel ID explicitly (default behavior persists to DB)
    python scripts/crawl_youtube.py --channel-id UCxxxxxxxxxxxxxx --pretty

    # Crawl every channel in YOUTUBE_TEST_CHANNEL_IDS, persist each
    python scripts/crawl_youtube.py

    # Just print, don't persist
    python scripts/crawl_youtube.py --channel-id UCxxxxxxxxxxxxxx --no-persist
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from social_data_collector.clients.base import RetryPolicy  # noqa: E402
from social_data_collector.clients.youtube import YouTubeClient  # noqa: E402
from social_data_collector.config import get_settings  # noqa: E402
from social_data_collector.normalizers.youtube import YouTubeNormalizer  # noqa: E402
from social_data_collector.persistence.repository import (  # noqa: E402
    run_in_transaction,
    sync_subject,
    sync_videos,
)
from social_data_collector.scheduler.tasks import _normalize_video  # noqa: E402


def _resolve_channel_ids(args: argparse.Namespace) -> list[str]:
    """Return the list of channel IDs to crawl.

    Priority: explicit --channel-id > YOUTUBE_TEST_CHANNEL_ID > YOUTUBE_TEST_CHANNEL_IDS.
    """
    if args.channel_id:
        return [args.channel_id]
    settings = get_settings()
    if settings.youtube.test_channel_id:
        return [settings.youtube.test_channel_id]
    if settings.youtube.test_channel_ids:
        return list(settings.youtube.test_channel_ids)
    print(
        "ERROR: No channel_id provided and YOUTUBE_TEST_CHANNEL_ID(S) is empty.",
        file=sys.stderr,
    )
    sys.exit(2)


def _crawl_one(
    channel_id: str,
    uploads_limit: int,
    retry_policy: RetryPolicy,
) -> tuple[dict, list, list, object, datetime]:
    """Crawl a single channel.

    Returns (raw_channel, recent_uploads, video_stats, subject, synced_at).

    Quota cost:
      1 (channels.list)
      + ceil(uploads_limit / 50) (playlistItems.list)
      + 1 (videos.list for stats, if uploads exist)
    """
    synced_at = datetime.now(UTC)
    settings = get_settings()

    with YouTubeClient(settings.youtube, retry_policy) as client:
        raw_channel = client.get_channel(channel_id)

        # get_recent_uploads accepts the full channel_response + limit.
        recent_uploads = client.get_recent_uploads(raw_channel, limit=uploads_limit)

        # Fetch per-video statistics (viewCount, likeCount, commentCount).
        # Quota: 1 unit per call for up to 50 video IDs.
        video_ids = [
            item["contentDetails"]["videoId"]
            for item in recent_uploads
            if item.get("contentDetails", {}).get("videoId")
        ]
        video_stats = client.get_video_details(video_ids) if video_ids else []

    subject = YouTubeNormalizer().normalize(
        platform_id=channel_id,
        raw_response=raw_channel,
        activity_data=recent_uploads,
        synced_at=synced_at,
        video_stats=video_stats,
    )
    return raw_channel, recent_uploads, video_stats, subject, synced_at


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crawl one or more YouTube Channels against the live Data API v3."
    )
    parser.add_argument(
        "--channel-id",
        help="YouTube Channel ID (UCxxxxxxx). Defaults to YOUTUBE_TEST_CHANNEL_ID(S).",
    )
    parser.add_argument(
        "--uploads-limit",
        type=int,
        default=50,
        help=(
            "Number of recent uploads to fetch for activity frequency "
            "(default: 50, max per page: 50; each extra page costs 1 quota unit)."
        ),
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
    if not settings.youtube.has_credentials:
        print(
            "ERROR: YouTube credentials are not configured. Set YOUTUBE_API_KEY.",
            file=sys.stderr,
        )
        return 1

    channel_ids = _resolve_channel_ids(args)
    retry_policy = RetryPolicy(max_attempts=3, initial_seconds=2, max_seconds=30)
    persist = not args.no_persist
    indent = 2 if args.pretty else None

    print(
        f"==> Will crawl {len(channel_ids)} channel(s) via YouTube Data API v3, "
        f"uploads_limit={args.uploads_limit}, persist={persist}"
    )

    failed: list[tuple[str, str]] = []

    for channel_id in channel_ids:
        print(f"\n========== {channel_id} ==========")
        try:
            raw_channel, recent_uploads, video_stats, subject, synced_at = _crawl_one(
                channel_id=channel_id,
                uploads_limit=args.uploads_limit,
                retry_policy=retry_policy,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"!!! Crawl failed for {channel_id}: {exc}", file=sys.stderr)
            failed.append((channel_id, f"crawl: {exc}"))
            continue

        print(f"\n--- {channel_id} raw channel response ---")
        print(json.dumps(raw_channel, indent=indent, default=str))
        print(f"\n--- {len(recent_uploads)} recent uploads ---")
        print(json.dumps(recent_uploads, indent=indent, default=str))
        print(f"\n--- {len(video_stats)} video stats ---")
        print(json.dumps(video_stats, indent=indent, default=str))
        print(f"\n--- {channel_id} normalized Subject ---")
        print(subject.model_dump_json(indent=indent))

        if not persist:
            continue

        try:
            videos = [
                v
                for v in (_normalize_video(v, str(subject.id), synced_at) for v in video_stats)
                if v is not None
            ]

            def _persist(session, _subject=subject, _videos=videos):
                sid = sync_subject(session, _subject)
                if _videos:
                    sync_videos(session, sid, _videos)
                return sid

            subject_id = run_in_transaction(_persist)
            print(
                f"\n==> Persisted subject_id={subject_id} with snapshot "
                f"captured_at={synced_at.isoformat()}"
            )
            if videos:
                print(f"    + {len(videos)} video(s) upserted")
        except Exception as exc:  # noqa: BLE001
            print(f"!!! Persist failed for {channel_id}: {exc}", file=sys.stderr)
            failed.append((channel_id, f"persist: {exc}"))

    if failed:
        print(
            f"\n{len(failed)} of {len(channel_ids)} channel(s) failed:",
            file=sys.stderr,
        )
        for cid, err in failed:
            print(f"  - {cid}: {err}", file=sys.stderr)
        return 1

    print(f"\n==> Done. {len(channel_ids)} channel(s) processed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
