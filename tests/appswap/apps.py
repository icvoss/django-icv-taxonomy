"""AppConfig for the swappable-model migration regression test (issue #21)."""

from __future__ import annotations

from django.apps import AppConfig


class SwapAppConfig(AppConfig):
    name = "appswap"
    label = "appswap"
    verbose_name = "icv-taxonomy swappable-model regression app"
    default_auto_field = "django.db.models.BigAutoField"
