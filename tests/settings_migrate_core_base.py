"""Settings for the ADR-052 icv-core base leg.

Identical to settings_migrate_defaults, except the model base is resolved
to icv-core's BaseModel via ICV_BASE_MODEL. Real migrations are enabled, so
`makemigrations --check` genuinely exercises the migration files against a
model state built on the icv-core base.

The point of the leg: _compat.BaseModel is byte-compatible with
icv_core.models.BaseModel, so BOTH resolutions must produce the same frozen
state and neither may report a diff. A drift in either direction shows up
here and nowhere else in CI.
"""

from __future__ import annotations

from settings_migrate_defaults import *  # noqa: F403

ICV_BASE_MODEL = "icv_core.models.BaseModel"
