"""Celery tasks for periodic and on-demand sync.

Task hierarchy:
- `sync_facebook_subject` / `sync_youtube_subject`: per-subject
  tasks. Marked retryable with the configured back-off.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from celery import shared_task
from social_common.constants import TASK_EVALUATE_SUBJECT_ALERTS
from social_common.enums import Platform
from social_common.errors import (
    PermanentPlatformError,
    SubjectNotFoundError,
    TransientPlatformError,
)
from social_common.schemas import Video
from sqlalchemy import select

from ..clients.base import RetryPolicy
from ..clients.facebook import FacebookClient
from ..clients.tiktok import TikTokClient
from ..clients.youtube import YouTubeAnalyticsClient, YouTubeClient
from ..config import get_settings
from ..logging_setup import get_logger
from ..normalizers.facebook import FacebookNormalizer, normalize_facebook_insights
from ..normalizers.tiktok import TikTokNormalizer
from ..normalizers.youtube import YouTubeNormalizer, pivot_analytics
from ..persistence.credential_resolver import resolve_credential
from ..persistence.models import SubjectModel
from ..persistence.repository import run_in_transaction, sync_subject, sync_videos

logger = get_logger("social_data_collector.scheduler.tasks")


def _retry_policy() -> RetryPolicy:
    return RetryPolicy.from_settings(get_settings().sync)


def _now() -> datetime:
    return datetime.now(UTC)


def _db_targets(platform: Platform) -> list[str]:
    """Read sync targets from the subjects table for a platform."""

    def _query(session: Any) -> list[str]:
        rows = (
            session.execute(
                select(SubjectModel.platform_id).where(SubjectModel.platform == platform)
            )
            .scalars()
            .all()
        )
        return [str(r) for r in rows]

    return run_in_transaction(_query)


def _facebook_targets() -> list[str]:
    settings = get_settings()
    if not settings.sync.facebook_enabled:
        logger.warning("sync.facebook.disabled_or_no_credentials")
        return []

    db_targets = _db_targets(Platform.FACEBOOK)
    if db_targets:
        return db_targets

    # Fallback: env-var seed list (first run / empty DB).
    if not settings.facebook.has_credentials:
        logger.warning("sync.facebook.disabled_or_no_credentials")
        return []
    return settings.facebook.test_page_ids


def _youtube_targets() -> list[str]:
    settings = get_settings()
    if not settings.sync.youtube_enabled:
        logger.warning("sync.youtube.disabled_or_no_credentials")
        return []

    db_targets = _db_targets(Platform.YOUTUBE)
    if db_targets:
        return db_targets

    # Fallback: env-var seed list (first run / empty DB).
    if not settings.youtube.has_credentials:
        logger.warning("sync.youtube.disabled_or_no_credentials")
        return []
    return settings.youtube.test_channel_ids


def _lookup_facebook_credentials(page_id: str) -> dict[str, Any] | None:
    """Look up per-subject Facebook credentials from the DB.

    Returns the full decrypted credential dict (access_token, page_id,
    optional app_id, app_secret) or None for legacy env-var fallback.
    """
    subject = run_in_transaction(
        lambda s: s.execute(
            select(SubjectModel).where(
                SubjectModel.platform == Platform.FACEBOOK,
                SubjectModel.platform_id == page_id,
            )
        ).scalar_one_or_none()
    )
    if subject is None or subject.credential_id is None:
        return None
    decrypted = resolve_credential(subject.credential_id)
    if decrypted is None:
        return None
    token = decrypted.get("access_token")
    if not token:
        logger.warning(
            "sync.credential.missing_field",
            platform="facebook",
            page_id=page_id,
            credential_id=str(subject.credential_id),
            field="access_token",
        )
    return decrypted


@shared_task(  # type: ignore[untyped-decorator]
    name="social_data_collector.scheduler.tasks.sync_facebook_subject",
    autoretry_for=(TransientPlatformError,),
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=True,
    max_retries=5,
)
def sync_facebook_subject(page_id: str) -> dict[str, Any]:
    logger.info("sync.start", platform="facebook", page_id=page_id)
    settings = get_settings()
    retry_policy = _retry_policy()
    synced_at = _now()

    creds = _lookup_facebook_credentials(page_id)
    access_token = creds.get("access_token") if creds else None
    app_id = creds.get("app_id") if creds else None
    app_secret = creds.get("app_secret") if creds else None

    try:
        with FacebookClient(
            settings.facebook,
            retry_policy,
            access_token=access_token,
            app_id=app_id,
            app_secret=app_secret,
        ) as client:
            raw_page = client.get_page(page_id)
            recent_posts = client.get_recent_posts(
                page_id, limit=settings.sync.activity_sample_size
            )
            raw_insights = client.get_page_insights(
                page_id,
                metrics=settings.facebook.insight_metrics,
            )
            insights = normalize_facebook_insights(raw_insights)
            photos = client.get_photos(page_id)
            videos = client.get_videos(page_id)
            extended_data = {
                "insights": insights,
                "photos": photos,
                "videos": videos,
            }
    except SubjectNotFoundError as exc:
        logger.error("sync.subject_not_found", platform="facebook", page_id=page_id, error=str(exc))
        return {"platform": "facebook", "page_id": page_id, "status": "subject_not_found"}
    except PermanentPlatformError as exc:
        logger.error("sync.permanent_failure", platform="facebook", page_id=page_id, error=str(exc))
        return {
            "platform": "facebook",
            "page_id": page_id,
            "status": "permanent_failure",
            "error": str(exc),
        }
    except TransientPlatformError as exc:
        logger.warning(
            "sync.quota_or_transient", platform="facebook", page_id=page_id, error=str(exc)
        )
        raise

    normalizer = FacebookNormalizer()
    subject = normalizer.normalize(
        platform_id=page_id,
        raw_response=raw_page,
        activity_data=recent_posts,
        synced_at=synced_at,
        extended_data=extended_data,
    )

    try:
        subject_id = run_in_transaction(lambda s: sync_subject(s, subject))
    except Exception as exc:  # noqa: BLE001
        logger.error("sync.persistence_error", platform="facebook", page_id=page_id, error=str(exc))
        raise

    logger.info(
        "sync.success",
        platform="facebook",
        page_id=page_id,
        subject_id=str(subject_id),
        followers=subject.followers,
        activity_frequency=subject.activity_frequency,
    )

    _trigger_alert_evaluation(str(subject_id))

    return {
        "platform": "facebook",
        "page_id": page_id,
        "subject_id": str(subject_id),
        "status": "ok",
    }


def _normalize_video(item: dict[str, Any], subject_id: str, synced_at: datetime) -> Video | None:
    """Build a Video Pydantic model from a videos.list API item."""
    vid = item.get("id")
    if not vid:
        return None
    snippet = item.get("snippet", {})
    statistics = item.get("statistics", {})
    content_details = item.get("contentDetails", {})
    published_at = snippet.get("publishedAt")
    if not published_at:
        return None
    try:
        parsed_published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None

    def _safe_int(val: Any) -> int:
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0

    thumbnails = snippet.get("thumbnails", {})
    thumbnail_url = None
    for size in ("high", "medium", "default"):
        thumb = thumbnails.get(size, {})
        url = thumb.get("url")
        if url:
            thumbnail_url = url
            break

    return Video(
        subject_id=UUID(subject_id),
        platform_video_id=str(vid),
        title=str(snippet.get("title", "")),
        description=snippet.get("description") or None,
        thumbnail_url=thumbnail_url,
        published_at=parsed_published,
        duration=content_details.get("duration") or None,
        view_count=_safe_int(statistics.get("viewCount")),
        like_count=_safe_int(statistics.get("likeCount")),
        comment_count=_safe_int(statistics.get("commentCount")),
        last_synced_at=synced_at,
    )


def _lookup_youtube_oauth_creds(channel_id: str) -> dict[str, str] | None:
    """Look up per-subject YouTube OAuth credentials from stored credentials.

    Returns a dict with keys ``access_token``, ``refresh_token``,
    ``client_id``, ``client_secret``, or ``None`` when no credential
    is linked.  The caller passes these as ``**kwargs`` to
    ``YouTubeAnalyticsClient``.
    """
    subject = run_in_transaction(
        lambda s: s.execute(
            select(SubjectModel).where(
                SubjectModel.platform == Platform.YOUTUBE,
                SubjectModel.platform_id == channel_id,
            )
        ).scalar_one_or_none()
    )
    if subject is None or subject.credential_id is None:
        return None
    decrypted = resolve_credential(subject.credential_id)
    if decrypted is None:
        return None
    _oauth_keys = frozenset({"access_token", "refresh_token", "client_id", "client_secret"})
    subset = {k: str(v) for k, v in decrypted.items() if k in _oauth_keys and v}
    if not subset:
        # No OAuth fields at all — API-key-only credential, not an error.
        return None
    if not subset.get("access_token"):
        logger.warning(
            "sync.credential.missing_field",
            platform="youtube",
            channel_id=channel_id,
            credential_id=str(subject.credential_id),
            field="access_token",
        )
    return subset


def _lookup_youtube_api_key(channel_id: str) -> str | None:
    """Look up a per-subject YouTube API key from stored credentials."""
    subject = run_in_transaction(
        lambda s: s.execute(
            select(SubjectModel).where(
                SubjectModel.platform == Platform.YOUTUBE,
                SubjectModel.platform_id == channel_id,
            )
        ).scalar_one_or_none()
    )
    if subject is None or subject.credential_id is None:
        return None
    decrypted = resolve_credential(subject.credential_id)
    if decrypted is None:
        return None
    key = decrypted.get("api_key")
    if not key:
        logger.warning(
            "sync.credential.missing_field",
            platform="youtube",
            channel_id=channel_id,
            credential_id=str(subject.credential_id),
            field="api_key",
        )
    return key


@shared_task(  # type: ignore[untyped-decorator]
    name="social_data_collector.scheduler.tasks.sync_youtube_subject",
    autoretry_for=(TransientPlatformError,),
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=True,
    max_retries=5,
)
def sync_youtube_subject(channel_id: str) -> dict[str, Any]:
    logger.info("sync.start", platform="youtube", channel_id=channel_id)
    settings = get_settings()
    retry_policy = _retry_policy()
    synced_at = _now()

    api_key = _lookup_youtube_api_key(channel_id)

    try:
        with YouTubeClient(settings.youtube, retry_policy, api_key=api_key) as client:
            raw_channel = client.get_channel(channel_id)
            uploads_playlist_id = YouTubeClient._extract_uploads_playlist_id(raw_channel)
            if uploads_playlist_id is None:
                logger.error(
                    "sync.no_uploads_playlist",
                    platform="youtube",
                    channel_id=channel_id,
                )
                return {
                    "platform": "youtube",
                    "channel_id": channel_id,
                    "status": "no_uploads_playlist",
                }
            recent_uploads = client.get_recent_uploads(
                raw_channel, limit=settings.sync.activity_sample_size
            )
            video_ids = [
                item["contentDetails"]["videoId"]
                for item in recent_uploads
                if item.get("contentDetails", {}).get("videoId")
            ]
            video_details = client.get_video_details(video_ids) if video_ids else []

        # YouTube Analytics (OAuth-optional): fetch time-series insights.
        analytics_raw: dict[str, Any] = {}
        analytics_metrics: list[dict[str, Any]] = []
        oauth_creds = _lookup_youtube_oauth_creds(channel_id)
        if oauth_creds and oauth_creds.get("access_token"):
            analytics_client = YouTubeAnalyticsClient(**oauth_creds)
            analytics_raw = analytics_client.get_channel_insights(channel_id)
            analytics_metrics = pivot_analytics(analytics_raw)
            if analytics_metrics:
                logger.info(
                    "sync.analytics.success",
                    platform="youtube",
                    channel_id=channel_id,
                    metric_count=len(analytics_metrics),
                )
    except SubjectNotFoundError as exc:
        logger.error(
            "sync.subject_not_found", platform="youtube", channel_id=channel_id, error=str(exc)
        )
        return {"platform": "youtube", "channel_id": channel_id, "status": "subject_not_found"}
    except PermanentPlatformError as exc:
        logger.error(
            "sync.permanent_failure", platform="youtube", channel_id=channel_id, error=str(exc)
        )
        return {
            "platform": "youtube",
            "channel_id": channel_id,
            "status": "permanent_failure",
            "error": str(exc),
        }
    except TransientPlatformError as exc:
        logger.warning(
            "sync.quota_or_transient", platform="youtube", channel_id=channel_id, error=str(exc)
        )
        raise

    normalizer = YouTubeNormalizer()
    subject = normalizer.normalize(
        platform_id=channel_id,
        raw_response=raw_channel,
        activity_data=recent_uploads,
        synced_at=synced_at,
        video_stats=video_details,
        analytics=analytics_metrics,  # will be added to extended_data
    )

    videos: list[Video] = [
        v
        for v in [_normalize_video(v, str(subject.id), synced_at) for v in video_details]
        if v is not None
    ]

    try:

        def _work(session: Any) -> UUID:
            subject_id = sync_subject(session, subject)
            if videos:
                sync_videos(session, subject_id, videos)
            return subject_id

        subject_id = run_in_transaction(_work)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "sync.persistence_error", platform="youtube", channel_id=channel_id, error=str(exc)
        )
        raise

    logger.info(
        "sync.success",
        platform="youtube",
        channel_id=channel_id,
        subject_id=str(subject_id),
        followers=subject.followers,
        activity_frequency=subject.activity_frequency,
        video_count=len(videos),
    )

    _trigger_alert_evaluation(str(subject_id))

    return {
        "platform": "youtube",
        "channel_id": channel_id,
        "subject_id": str(subject_id),
        "status": "ok",
        "video_count": len(videos),
    }


def _tiktok_targets() -> list[str]:
    settings = get_settings()
    if not settings.sync.tiktok_enabled:
        logger.warning("sync.tiktok.disabled")
        return []

    db_targets = _db_targets(Platform.TIKTOK)
    if db_targets:
        return db_targets

    if settings.tiktok.test_open_id:
        return [settings.tiktok.test_open_id]
    return []


def _lookup_tiktok_credentials(open_id: str) -> dict[str, Any] | None:
    """Look up per-subject TikTok credentials from the DB.

    Returns the full decrypted credential dict (access_token,
    refresh_token, client_key, client_secret).
    """
    subject = run_in_transaction(
        lambda s: s.execute(
            select(SubjectModel).where(
                SubjectModel.platform == Platform.TIKTOK,
                SubjectModel.platform_id == open_id,
            )
        ).scalar_one_or_none()
    )
    if subject is None or subject.credential_id is None:
        return None
    decrypted = resolve_credential(subject.credential_id)
    if decrypted is None:
        return None
    token = decrypted.get("access_token")
    if not token:
        logger.warning(
            "sync.credential.missing_field",
            platform="tiktok",
            open_id=open_id,
            credential_id=str(subject.credential_id),
            field="access_token",
        )
    return decrypted


@shared_task(  # type: ignore[untyped-decorator]
    name="social_data_collector.scheduler.tasks.sync_tiktok_subject",
    autoretry_for=(TransientPlatformError,),
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=True,
    max_retries=5,
)
def sync_tiktok_subject(open_id: str) -> dict[str, Any]:
    logger.info("sync.start", platform="tiktok", open_id=open_id)
    settings = get_settings()
    retry_policy = _retry_policy()
    synced_at = _now()

    creds = _lookup_tiktok_credentials(open_id)
    if not creds or not creds.get("access_token"):
        logger.error(
            "sync.no_credentials",
            platform="tiktok",
            open_id=open_id,
        )
        return {"platform": "tiktok", "open_id": open_id, "status": "no_credentials"}

    access_token = str(creds["access_token"])

    try:
        with TikTokClient(
            access_token=access_token,
            retry_policy=retry_policy,
        ) as client:
            user_info = client.get_user_info(open_id)
            videos = client.get_video_list(
                open_id,
                max_count=settings.sync.activity_sample_size,
                overall_limit=100,
            )
    except SubjectNotFoundError as exc:
        logger.error(
            "sync.subject_not_found", platform="tiktok", open_id=open_id, error=str(exc)
        )
        return {"platform": "tiktok", "open_id": open_id, "status": "subject_not_found"}
    except PermanentPlatformError as exc:
        logger.error(
            "sync.permanent_failure", platform="tiktok", open_id=open_id, error=str(exc)
        )
        return {
            "platform": "tiktok",
            "open_id": open_id,
            "status": "permanent_failure",
            "error": str(exc),
        }
    except TransientPlatformError as exc:
        logger.warning(
            "sync.quota_or_transient", platform="tiktok", open_id=open_id, error=str(exc)
        )
        raise

    normalizer = TikTokNormalizer()
    subject = normalizer.normalize(
        platform_id=open_id,
        raw_response=user_info,
        activity_data=videos,
        synced_at=synced_at,
    )

    try:
        subject_id = run_in_transaction(lambda s: sync_subject(s, subject))
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "sync.persistence_error", platform="tiktok", open_id=open_id, error=str(exc)
        )
        raise

    logger.info(
        "sync.success",
        platform="tiktok",
        open_id=open_id,
        subject_id=str(subject_id),
        followers=subject.followers,
        activity_frequency=subject.activity_frequency,
        video_count=len(videos),
    )

    _trigger_alert_evaluation(str(subject_id))

    return {
        "platform": "tiktok",
        "open_id": open_id,
        "subject_id": str(subject_id),
        "status": "ok",
        "video_count": len(videos),
    }


def sync_all_tiktok_subjects() -> int:
    targets = _tiktok_targets()
    failures = 0
    for open_id in targets:
        try:
            sync_tiktok_subject(open_id)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            logger.error(
                "sync.cli.failure", platform="tiktok", open_id=open_id, error=str(exc)
            )
    return 0 if failures == 0 else 1


def _trigger_alert_evaluation(subject_id: str) -> None:
    """Fire-and-forget: dispatch an alert evaluation task to the alert engine.

    Best-effort only: if the alert-engine worker is not running, the
    task sits in Redis until a worker picks it up.
    """
    try:
        from social_data_collector.scheduler.celery_app import celery_app

        logger.info("tasks.trigger_alert_evaluation", subject_id=subject_id)
        celery_app.send_task(TASK_EVALUATE_SUBJECT_ALERTS, args=[subject_id])
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "tasks.trigger_alert_evaluation_failed",
            subject_id=subject_id,
            error=str(exc),
        )


def sync_all_facebook_subjects() -> int:
    """Run all Facebook syncs synchronously and return aggregate exit code.

    Used by the CLI. Each subject is wrapped in try/except so a single
    failure does not abort the rest.
    """
    targets = _facebook_targets()
    failures = 0
    for page_id in targets:
        try:
            sync_facebook_subject(page_id)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            logger.error("sync.cli.failure", platform="facebook", page_id=page_id, error=str(exc))
    return 0 if failures == 0 else 1


def sync_all_youtube_subjects() -> int:
    targets = _youtube_targets()
    failures = 0
    for channel_id in targets:
        try:
            sync_youtube_subject(channel_id)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            logger.error(
                "sync.cli.failure", platform="youtube", channel_id=channel_id, error=str(exc)
            )
    return 0 if failures == 0 else 1
