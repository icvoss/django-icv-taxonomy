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
    "icv_core",
    "icv_tree",
    "icv_taxonomy",
]

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
