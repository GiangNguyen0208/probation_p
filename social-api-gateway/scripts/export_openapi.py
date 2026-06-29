"""Export the gateway's live OpenAPI schema to a JSON file.

Usage: python scripts/export_openapi.py

Writes to social-mini-app/src/api/openapi.json, relative to the repo root.
The generated file is committed and used by openapi-typescript to produce
typed API clients for the Mini App.
"""

from pathlib import Path

from social_api_gateway.main import _custom_openapi, create_app

_REPO_ROOT = Path(__file__).resolve().parents[2]

app = create_app()
schema = _custom_openapi(app)

out = _REPO_ROOT / "social-mini-app" / "src" / "api" / "openapi.json"
out.write_text(__import__("json").dumps(schema, indent=2, default=str))
print(f"Wrote {out}")
