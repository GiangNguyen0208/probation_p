# social-common

Shared library for the Social Intelligence Platform. Contains the unified data contracts every service depends on: the `Subject` schema, `ActivitySnapshot`, `AlertRule`, and the platform/status enums.

This package is a pure data layer with no runtime dependencies beyond Pydantic. It is versioned and pinned by every service that imports it.

## Public API

- `social_common.enums.Platform`
- `social_common.enums.SubjectStatus`
- `social_common.enums.AlertRuleType`
- `social_common.schemas.Subject`
- `social_common.schemas.ActivitySnapshot`
- `social_common.schemas.AlertRule`
- `social_common.errors.SubjectNotFoundError`
- `social_common.errors.PermanentPlatformError`
- `social_common.errors.TransientPlatformError`

## Install

```
pip install -e ./social-common
```

Any change to the schemas in this package is a breaking change for all downstream services and must go through a version bump.
