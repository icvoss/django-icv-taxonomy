"""
Django settings for the swappable-model migration regression test (issue
#21, BR-TAX-050).

Deliberately DOES declare ICV_TAXONOMY_VOCABULARY_MODEL and
ICV_TAXONOMY_TERM_MODEL, pointed at appswap's own concrete subclasses of
AbstractVocabulary/AbstractTerm, and does NOT disable migrations for
icv_taxonomy or appswap. This is the configuration of a consuming project
that exercises the documented swappable-model seam. `migrate` and
`makemigrations --check` must both succeed with no drift against this
settings module; see test_migrations_swapped.py.
"""

from __future__ import annotations

SECRET_KEY = "icv-taxonomy-migrate-swapped-test-secret-key"  # noqa: S105

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "icv_tree",
    "icv_taxonomy",
    "appswap",
]

# icv-core is an optional extra; add it only when installed (mirrors
# tests/settings.py and tests/settings_migrate_defaults.py).
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

# The setting under test: point Term/Vocabulary at appswap's own subclasses,
# exactly as a real consuming project would.
ICV_TAXONOMY_VOCABULARY_MODEL = "appswap.AppSwapVocabulary"
ICV_TAXONOMY_TERM_MODEL = "appswap.AppSwapTerm"
