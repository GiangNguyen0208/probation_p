#!/usr/bin/env python3
"""Facebook Page diagnostic probe tool.

Developer-only CLI that discovers every field and insight metric a
specific Facebook Page exposes, given a valid access token. Inspired
by the pilot ``probePageEverything()`` function.

Usage:
    python scripts/probe_facebook.py --page-id <id> --token <token> [--pretty]
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

# Candidate metrics to probe. Includes current defaults, legacy metrics
# (to confirm deprecation), and newer replacements.
CANDIDATE_METRICS = [
    # Current production defaults (config.py)
    "page_media_view",
    "page_total_media_view_unique",
    "page_media_view_unique",
    "page_views_total",
    "page_post_engagements",
    "page_follows",
    "page_daily_follows",
    "page_daily_follows_unique",
    "page_daily_unfollows_unique",
    "page_actions_post_reactions_total",
    # Post-level metrics
    "page_posts_impressions",
    "page_posts_impressions_unique",
    "page_reactions_by_type_total",
    # Legacy / deprecated metrics (kept to verify they are gone)
    "page_impressions",
    "page_impressions_unique",
    "page_impressions_paid",
    "page_impressions_organic_unique_v2",
    "page_engaged_users",
    "page_fans",
    "page_fan_adds",
    "page_fan_adds_unique",
    "page_fan_removes",
    "page_video_views",
    "page_total_actions",
    "page_consumptions",
    "page_places_checkin_total",
]

DEFAULT_GRAPH_VERSION = "v25.0"


def _auth_params(access_token: str, app_secret: str | None, **params: str) -> dict[str, str]:
    params["access_token"] = access_token
    if app_secret:
        params["appsecret_proof"] = hmac.new(
            app_secret.encode(),
            access_token.encode(),
            hashlib.sha256,
        ).hexdigest()
    return params


def _graph_get(base_url: str, path: str, params: dict[str, str]) -> dict[str, Any]:
    url = f"{base_url}{path}"
    resp = httpx.get(url, params=params, timeout=30.0)
    body: dict[str, Any] = resp.json()
    if resp.status_code >= 400 or (body.get("error") is not None):
        raise RuntimeError(f"Graph error {resp.status_code}: {body.get('error', body)}")
    return body


def probe_page(
    page_id: str,
    access_token: str,
    app_secret: str | None = None,
    graph_version: str = DEFAULT_GRAPH_VERSION,
) -> dict[str, Any]:
    base_url = f"https://graph.facebook.com/{graph_version}"

    # 1. Catalog fields via metadata=1
    metadata: dict[str, Any] = {}
    try:
        metadata = _graph_get(
            base_url,
            f"/{page_id}",
            _auth_params(access_token, app_secret, metadata="1"),
        )
    except RuntimeError as exc:
        metadata = {"error": str(exc)}

    field_defs: list[dict[str, Any]] = (
        metadata.get("metadata", {}).get("fields", [])
        if isinstance(metadata, dict)
        else []
    )
    connections = (
        metadata.get("metadata", {}).get("connections")
        if isinstance(metadata, dict)
        else None
    )

    # 2. Fetch each field individually
    fields: dict[str, Any] = {}
    for field_def in field_defs:
        name = field_def.get("name", "")
        if not name:
            continue
        try:
            value = _graph_get(
                base_url,
                f"/{page_id}",
                _auth_params(access_token, app_secret, fields=name),
            )
            fields[name] = {
                "description": field_def.get("description"),
                "value": value.get(name),
            }
        except RuntimeError as exc:
            fields[name] = {
                "description": field_def.get("description"),
                "error": str(exc),
            }

    # 3. Probe each insight metric individually
    insights: dict[str, Any] = {}
    for metric in CANDIDATE_METRICS:
        try:
            data = _graph_get(
                base_url,
                f"/{page_id}/insights",
                _auth_params(access_token, app_secret, metric=metric, period="day"),
            )
            arr = data.get("data", [])
            first = arr[0] if isinstance(arr, list) and arr else None
            if first:
                insights[metric] = {
                    "valid": True,
                    "title": first.get("title"),
                    "description": first.get("description"),
                    "values": first.get("values"),
                }
            else:
                insights[metric] = {"valid": True, "empty": True}
        except RuntimeError as exc:
            insights[metric] = {"valid": False, "error": str(exc)}

    return {
        "page_id": page_id,
        "probed_at": datetime.now(UTC).isoformat(),
        "connections": connections,
        "field_count": len(fields),
        "fields": fields,
        "insights_probe": insights,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe a Facebook Page for all available fields and insights")
    parser.add_argument("--page-id", required=True, help="Facebook Page ID")
    parser.add_argument("--token", required=True, help="Page or App access token")
    parser.add_argument("--app-secret", default=None, help="Optional app secret for appsecret_proof")
    parser.add_argument("--graph-version", default=DEFAULT_GRAPH_VERSION, help="Graph API version")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--out", type=Path, default=None, help="Optional output file path")
    args = parser.parse_args(argv)

    try:
        result = probe_page(args.page_id, args.token, args.app_secret, args.graph_version)
    except Exception as exc:  # noqa: BLE001
        print(f"Probe failed: {exc}", file=sys.stderr)
        return 1

    indent = 2 if args.pretty else None
    json_out = json.dumps(result, indent=indent, default=str, ensure_ascii=False)

    if args.out:
        args.out.write_text(json_out, encoding="utf-8")
        print(f"Probe result written to {args.out}")
    else:
        print(json_out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
