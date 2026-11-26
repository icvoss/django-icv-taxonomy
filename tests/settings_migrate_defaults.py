"""
Django settings for the migration-defaults regression test.

Deliberately does NOT declare ICV_TAXONOMY_VOCABULARY_MODEL or
ICV_TAXONOMY_TERM_MODEL, and does NOT disable migrations for icv_taxonomy.
This is the configuration of a consuming project that installs icv_taxonomy
without opting into model swapping. `migrate` and `makemigrations --check`
must succeed against this settings module; see test_migrations_defaults.py.
"""

from __future__ import annotations

SECRET_KEY = "icv-taxonomy-migrate-test-secret-key"  # noqa: S105

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "icv_tree",
    "icv_taxonomy",
]

# icv-core is an optional extra; add it only when installed (mirrors
# tests/settings.py). This regression test is about the icv_taxonomy swappable
# settings, not icv-core, so it must run whether or not core is present, exactly
# as a consuming project's CI would (icv-core absent is the common case).
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

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"

# icv-tree requires these; it is not itself swappable so this is unrelated
# to the bug under test.
ICV_TREE_PATH_SEPARATOR = "/"
ICV_TREE_STEP_LENGTH = 4
ICV_TREE_MAX_PATH_LENGTH = 255
ICV_TREE_ENABLE_CTE = False
ICV_TREE_REBUILD_BATCH_SIZE = 1000
ICV_TREE_CHECK_ON_SAVE = False

# Intentionally absent: ICV_TAXONOMY_VOCABULARY_MODEL, ICV_TAXONOMY_TERM_MODEL.
# The migrations must fall back to the package defaults
# ("icv_taxonomy.Vocabulary", "icv_taxonomy.Term") via getattr().


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
