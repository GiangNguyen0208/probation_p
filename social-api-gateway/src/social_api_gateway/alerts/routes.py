"""/v1/subjects/{subject_id}/alerts and /v1/alerts/{rule_id} endpoints.

Write operations (POST, PUT, DELETE) require an internal API key.
External keys receive 403 Forbidden. Read operations (GET) are
available to all authenticated keys.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from social_common.envelope import ResponseMeta
from social_common.schemas import AlertRule
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.models import APIKeyModel, APIKeyTier
from ..deps import get_db_session, rate_limit
from ..logging_setup import get_logger
from .models import AlertRuleModel
from .repository import AlertRepository
from .schemas import (
    AlertLogListResponse,
    AlertRuleCreate,
    AlertRuleListResponse,
    AlertRuleResponse,
    AlertRuleUpdate,
)

logger = get_logger("social_api_gateway.alerts.routes")

router = APIRouter(tags=["alerts"])


def _require_internal(api_key: APIKeyModel) -> None:
    """Raise 403 if the key is not internal tier."""
    if api_key.tier != APIKeyTier.INTERNAL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "internal_key_required",
                "message": "This endpoint requires an internal API key.",
            },
        )


def _model_to_schema(rule: AlertRuleModel) -> AlertRule:
    return AlertRule.model_validate(rule)


@router.get(
    "/v1/subjects/{subject_id}/alerts",
    response_model=AlertRuleListResponse,
    summary="List alert rules for a subject",
    description=(
        "Return all alert rules for a subject, newest first. "
        "Supports `active_only` filter and pagination."
    ),
    responses={
        401: {"description": "Missing or invalid API key"},
        404: {"description": "Subject not found"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def list_alerts(
    subject_id: UUID,
    active_only: bool = Query(False, description="Only return active rules."),
    page: int = Query(1, ge=1, description="1-indexed page number."),
    limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)."),
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
) -> AlertRuleListResponse:
    repo = AlertRepository(db)
    offset = (page - 1) * limit
    rows, total = await repo.list_rules(
        subject_id=subject_id,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )
    data = [_model_to_schema(r) for r in rows]
    return AlertRuleListResponse(
        data=data,
        meta=ResponseMeta(page=page, limit=limit, total=total),
    )


@router.post(
    "/v1/subjects/{subject_id}/alerts",
    status_code=status.HTTP_201_CREATED,
    response_model=AlertRuleResponse,
    summary="Create an alert rule for a subject",
    description="Create a new alert rule. Requires an internal API key.",
    responses={
        401: {"description": "Missing or invalid API key"},
        403: {"description": "Internal API key required"},
        404: {"description": "Subject not found"},
        422: {"description": "Invalid request body"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def create_alert(
    subject_id: UUID,
    body: AlertRuleCreate,
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
) -> AlertRuleResponse:
    _require_internal(api_key)

    repo = AlertRepository(db)
    rule = AlertRuleModel(
        subject_id=subject_id,
        rule_type=body.rule_type,
        threshold=body.threshold,
        cooldown_seconds=body.cooldown_seconds,
        channel_id=body.channel_id,
    )
    created = await repo.create_rule(rule)
    logger.info("alert.created", rule_id=str(created.id), subject_id=str(subject_id))
    return AlertRuleResponse(data=_model_to_schema(created), meta=ResponseMeta())


@router.put(
    "/v1/alerts/{rule_id}",
    response_model=AlertRuleResponse,
    summary="Update an alert rule",
    description="Update an existing alert rule. Requires an internal API key.",
    responses={
        401: {"description": "Missing or invalid API key"},
        403: {"description": "Internal API key required"},
        404: {"description": "Rule not found"},
        422: {"description": "Invalid request body"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def update_alert(
    rule_id: UUID,
    body: AlertRuleUpdate,
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
) -> AlertRuleResponse:
    _require_internal(api_key)

    repo = AlertRepository(db)
    existing = await repo.get_rule(rule_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "rule_not_found", "message": f"Alert rule {rule_id} not found."},
        )

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return AlertRuleResponse(data=_model_to_schema(existing), meta=ResponseMeta())

    updated = await repo.update_rule(rule_id, updates)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "rule_not_found", "message": f"Alert rule {rule_id} not found."},
        )
    logger.info("alert.updated", rule_id=str(rule_id))
    return AlertRuleResponse(data=_model_to_schema(updated), meta=ResponseMeta())


@router.delete(
    "/v1/alerts/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an alert rule",
    description="Delete an alert rule. Requires an internal API key.",
    responses={
        401: {"description": "Missing or invalid API key"},
        403: {"description": "Internal API key required"},
        404: {"description": "Rule not found"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def delete_alert(
    rule_id: UUID,
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    _require_internal(api_key)

    repo = AlertRepository(db)
    deleted = await repo.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "rule_not_found", "message": f"Alert rule {rule_id} not found."},
        )
    logger.info("alert.deleted", rule_id=str(rule_id))


@router.get(
    "/v1/subjects/{subject_id}/alerts/logs",
    response_model=AlertLogListResponse,
    summary="List alert logs for a subject",
    description=("Return alert history for a subject, newest first. Supports pagination."),
    responses={
        401: {"description": "Missing or invalid API key"},
        404: {"description": "Subject not found"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def list_alert_logs(
    subject_id: UUID,
    page: int = Query(1, ge=1, description="1-indexed page number."),
    limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)."),
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
) -> AlertLogListResponse:
    from social_common.schemas import AlertLog

    repo = AlertRepository(db)
    offset = (page - 1) * limit
    rows, total = await repo.list_alert_logs(subject_id=subject_id, limit=limit, offset=offset)
    data = [AlertLog.model_validate(r) for r in rows]
    return AlertLogListResponse(
        data=data,
        meta=ResponseMeta(page=page, limit=limit, total=total),
    )
