"""
Django settings for icv-taxonomy tests.

Minimal configuration — MIGRATION_MODULES set to None so syncdb creates
tables directly without running migrations.
"""

from __future__ import annotations

SECRET_KEY = "icv-taxonomy-test-secret-key"  # noqa: S105

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "icv_tree",
    "icv_taxonomy",
    "taxonomy_testapp",
]

# Add icv_core if installed (avoids AuditEntry app_label error in CI)
try:
    import icv_core  # noqa: F401

    INSTALLED_APPS.insert(2, "icv_core")
except ImportError:
    pass

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

MIGRATION_MODULES = {
    "icv_tree": None,
    "icv_taxonomy": None,
    "taxonomy_testapp": None,
    "contenttypes": None,
    "auth": None,
    "admin": None,
    "sessions": None,
}

# Suppress icv_core migrations if installed
try:
    import icv_core  # noqa: F401

    MIGRATION_MODULES["icv_core"] = None
except ImportError:
    pass

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ROOT_URLCONF = "django.urls"

# icv-tree settings
ICV_TREE_PATH_SEPARATOR = "/"
ICV_TREE_STEP_LENGTH = 4
ICV_TREE_MAX_PATH_LENGTH = 255
ICV_TREE_ENABLE_CTE = False
ICV_TREE_REBUILD_BATCH_SIZE = 1000
ICV_TREE_CHECK_ON_SAVE = False

# icv-taxonomy settings (defaults)
ICV_TAXONOMY_AUTO_SLUG = True
ICV_TAXONOMY_CASE_SENSITIVE_SLUGS = False
ICV_TAXONOMY_ENFORCE_VOCABULARY_TYPE = True


# ADR-101 decision 3: the logging-handler boot check (icv_taxonomy.E004) is an
# Error, so every settings module that runs system checks (makemigrations,
# migrate, check) must route the package logger to a handler. Propagation
# stays on so caplog and the root logger still see the records, and the root
# handler covers any sibling ICV package installed alongside this one.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "loggers": {
        "icv_taxonomy": {"handlers": ["null"], "level": "WARNING", "propagate": True},
    },
    "root": {"handlers": ["null"]},
}
