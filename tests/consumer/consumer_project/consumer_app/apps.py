"""AppConfig for the icv-taxonomy consumer smoke-test harness's local app."""

from __future__ import annotations

from django.apps import AppConfig


class ConsumerAppConfig(AppConfig):
    name = "consumer_project.consumer_app"
    label = "consumer_app"
    verbose_name = "icv-taxonomy consumer smoke-test app"
    default_auto_field = "django.db.models.BigAutoField"
