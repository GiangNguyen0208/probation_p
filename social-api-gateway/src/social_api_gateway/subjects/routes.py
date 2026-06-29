"""/v1/subjects endpoints.

The cache is read-through with TTL-based invalidation. On cache miss,
the route queries the DB, builds the response envelope, stores it in
Redis with the configured TTL, and returns it. Subsequent requests
within the TTL window hit the cache.

The activity endpoint checks the subject exists before querying
snapshots so it can return 404 with the same shape as the single-
subject endpoint.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID

from celery import Celery
from fastapi import APIRouter, Depends, HTTPException, Query, status
from social_common.enums import Platform, SubjectStatus
from social_common.envelope import ResponseMeta
from social_common.schemas import ActivitySnapshot, Subject, Video
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.models import APIKeyModel
from ..cache.service import CacheService, hash_query_params
from ..config import get_settings
from ..deps import get_cache_service, get_celery_client, get_db_session, rate_limit
from ..logging_setup import get_logger
from .repository import SubjectRepository
from .schemas import ActivityListResponse, SubjectListResponse, SubjectResponse, VideoListResponse

logger = get_logger("social_api_gateway.subjects.routes")

router = APIRouter(prefix="/v1/subjects", tags=["subjects"])


@router.get(
    "",
    response_model=SubjectListResponse,
    summary="List subjects",
    description=(
        "List monitored subjects with optional filters and pagination. "
        "Sorted by `last_synced_at` descending. Cached for "
        "`CACHE_LIST_TTL_SECONDS` (default 60s)."
    ),
    responses={
        401: {"description": "Missing or invalid API key"},
        422: {"description": "Invalid query parameters"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def list_subjects(
    platform: Platform | None = Query(
        None, description="Filter by platform: `facebook` or `youtube`."
    ),
    status_filter: SubjectStatus | None = Query(
        None, alias="status", description="Filter by status: `active`, `inactive`, or `suspended`."
    ),
    q: str | None = Query(None, description="Case-insensitive search on name or platform_id."),
    last_synced_from: datetime | None = Query(
        None,
        description="Include only subjects with `last_synced_at >=` this timestamp (ISO 8601).",
    ),
    last_synced_to: datetime | None = Query(
        None,
        description="Include only subjects with `last_synced_at <=` this timestamp (ISO 8601).",
    ),
    page: int = Query(1, ge=1, description="1-indexed page number."),
    limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)."),
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
) -> SubjectListResponse:
    settings = get_settings()
    offset = (page - 1) * limit

    platform_enum = platform
    status_enum = status_filter

    query_hash = hash_query_params(
        platform=platform_enum.value if platform_enum else None,
        status=status_enum.value if status_enum else None,
        q=q,
        lsf=last_synced_from.isoformat() if last_synced_from else None,
        lst=last_synced_to.isoformat() if last_synced_to else None,
        page=page,
        limit=limit,
    )
    cache_key = f"cache:subjects:list:{query_hash}"

    cached = await cache.get(cache_key)
    if cached is not None:
        logger.info("subjects.list.cache_hit", cache_key=cache_key)
        return SubjectListResponse.model_validate(cached)

    repo = SubjectRepository(db)
    rows, total = await repo.list_subjects(
        platform=platform_enum,
        status=status_enum,
        q=q,
        last_synced_from=last_synced_from,
        last_synced_to=last_synced_to,
        limit=limit,
        offset=offset,
    )

    data = [Subject.model_validate(row) for row in rows]
    response = SubjectListResponse(
        data=data,
        meta=ResponseMeta(page=page, limit=limit, total=total),
    )

    await cache.set(
        cache_key,
        response.model_dump(mode="json"),
        ttl_seconds=settings.cache.list_ttl_seconds,
    )
    return response


@router.get(
    "/{subject_id}",
    response_model=SubjectResponse,
    summary="Get a single subject",
    description="Fetch a single subject by its system-generated UUID.",
    responses={
        401: {"description": "Missing or invalid API key"},
        404: {"description": "Subject not found"},
        422: {"description": "Invalid UUID"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def get_subject(
    subject_id: UUID,
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
) -> SubjectResponse:
    settings = get_settings()
    cache_key = f"cache:subject:{subject_id}"

    cached = await cache.get(cache_key)
    if cached is not None:
        logger.info("subjects.get.cache_hit", subject_id=str(subject_id))
        return SubjectResponse.model_validate(cached)

    repo = SubjectRepository(db)
    subject = await repo.get_subject(subject_id)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "subject_not_found", "message": f"Subject {subject_id} not found."},
        )

    data = Subject.model_validate(subject)
    response = SubjectResponse(data=data, meta=ResponseMeta())
    await cache.set(
        cache_key,
        response.model_dump(mode="json"),
        ttl_seconds=settings.cache.subject_ttl_seconds,
    )
    return response


@router.get(
    "/{subject_id}/activity",
    response_model=ActivityListResponse,
    summary="Get activity time-series for a subject",
    description=(
        "Return historical activity snapshots for a subject, newest first. "
        "Optional `from` and `to` ISO 8601 timestamps bound the time range. "
        "Capped at `limit` rows (default 1000, max 10000)."
    ),
    responses={
        401: {"description": "Missing or invalid API key"},
        404: {"description": "Subject not found"},
        422: {"description": "Invalid UUID or timestamps"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def get_activity(
    subject_id: UUID,
    from_: datetime | None = Query(
        None, alias="from", description="Lower bound on `captured_at` (ISO 8601)."
    ),
    to: datetime | None = Query(None, description="Upper bound on `captured_at` (ISO 8601)."),
    limit: int = Query(1000, ge=1, le=10000, description="Max snapshots to return."),
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
) -> ActivityListResponse:
    settings = get_settings()
    query_hash = hash_query_params(
        f=from_.isoformat() if from_ else None,
        t=to.isoformat() if to else None,
        l=limit,
    )
    cache_key = f"cache:subject:{subject_id}:activity:{query_hash}"

    cached = await cache.get(cache_key)
    if cached is not None:
        logger.info("activity.list.cache_hit", subject_id=str(subject_id))
        return ActivityListResponse.model_validate(cached)

    repo = SubjectRepository(db)
    subject = await repo.get_subject(subject_id)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "subject_not_found", "message": f"Subject {subject_id} not found."},
        )

    snapshots = await repo.get_activity(subject_id, from_dt=from_, to_dt=to, limit=limit)
    data = [ActivitySnapshot.model_validate(s) for s in snapshots]
    response = ActivityListResponse(
        data=data,
        meta=ResponseMeta(page=1, limit=limit, total=len(snapshots)),
    )
    await cache.set(
        cache_key,
        response.model_dump(mode="json"),
        ttl_seconds=settings.cache.activity_ttl_seconds,
    )
    return response


@router.post(
    "/{subject_id}/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger on-demand sync for a subject",
    description="Enqueue a background task to sync data for this subject.",
    responses={
        401: {"description": "Missing or invalid API key"},
        404: {"description": "Subject not found"},
        422: {"description": "Invalid UUID"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def trigger_sync(
    subject_id: UUID,
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
    celery_app: Celery = Depends(get_celery_client),
) -> dict[str, str]:
    repo = SubjectRepository(db)
    subject = await repo.get_subject(subject_id)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "subject_not_found", "message": f"Subject {subject_id} not found."},
        )

    if subject.platform == Platform.FACEBOOK:
        task_name = "social_data_collector.scheduler.tasks.sync_facebook_subject"
    elif subject.platform == Platform.YOUTUBE:
        task_name = "social_data_collector.scheduler.tasks.sync_youtube_subject"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "unsupported_platform",
                "message": f"Sync not supported for platform {subject.platform}.",
            },
        )

    # Use asyncio.to_thread since send_task does synchronous I/O
    async_result = await asyncio.to_thread(
        celery_app.send_task,
        task_name,
        args=[subject.platform_id],
    )

    logger.info("sync.triggered", subject_id=str(subject_id), task_id=async_result.id)
    return {"status": "accepted", "task_id": async_result.id}


@router.get(
    "/{subject_id}/videos",
    response_model=VideoListResponse,
    summary="List videos for a subject",
    description=(
        "Return tracked videos for a YouTube subject, newest first. "
        "Each video includes the latest observed metrics (views, likes, comments). "
        "Capped at `limit` rows (default 50, max 100)."
    ),
    responses={
        401: {"description": "Missing or invalid API key"},
        404: {"description": "Subject not found"},
        422: {"description": "Invalid UUID"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def list_videos(
    subject_id: UUID,
    page: int = Query(1, ge=1, description="1-indexed page number."),
    limit: int = Query(50, ge=1, le=100, description="Items per page."),
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
) -> VideoListResponse:
    repo = SubjectRepository(db)
    subject = await repo.get_subject(subject_id)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "subject_not_found", "message": f"Subject {subject_id} not found."},
        )

    offset = (page - 1) * limit
    rows, total = await repo.list_videos(subject_id, limit=limit, offset=offset)
    data = [Video.model_validate(row) for row in rows]
    return VideoListResponse(
        data=data,
        meta=ResponseMeta(page=page, limit=limit, total=total),
    )
