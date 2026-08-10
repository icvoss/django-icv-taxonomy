"""Settings for the icv-taxonomy consumer smoke-test harness (ADR-027).

Configures the swappable Vocabulary/Term models via consumer_app, the way a
real installing project would: ICV_TAXONOMY_VOCABULARY_MODEL and
ICV_TAXONOMY_TERM_MODEL point at consumer_app's own subclasses, not the
package's shipped defaults, so this harness actually exercises the
swappable-model seam and the TreeNode inheritance (AbstractTerm extends
icv_tree.models.TreeNode), not just the default configuration already
covered by tests/settings.py.
"""

from __future__ import annotations

SECRET_KEY = "icv-taxonomy-consumer-smoke-test-key-not-secret"  # noqa: S105

DEBUG = False

INSTALLED_APPS = [
    "django.contrib.contenttypes",  # required for generic tagging (TermAssociation)
    "django.contrib.auth",
    "icv_tree",
    "icv_taxonomy",
    "consumer_project.consumer_app",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "consumer_smoke_test.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True

# Swappable models: point at consumer_app's own subclasses, exactly as a real
# consuming project would, so this harness exercises the swappable-model seam
# and TreeNode inheritance rather than the shipped defaults.
ICV_TAXONOMY_VOCABULARY_MODEL = "consumer_app.ConsumerVocabulary"
ICV_TAXONOMY_TERM_MODEL = "consumer_app.ConsumerTerm"
