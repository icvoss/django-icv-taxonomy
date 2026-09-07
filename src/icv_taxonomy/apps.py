"""AppConfig for icv-taxonomy."""

from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class IcvTaxonomyConfig(AppConfig):
    name = "icv_taxonomy"
    label = "icv_taxonomy"
    verbose_name = _("ICV Taxonomy")
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Connect signal handlers and register system checks at startup."""
        from . import checks, handlers  # noqa: F401 (checks registers system checks on import)

        # Connect the Vocabulary/Term post_save/pre_delete handlers, per
        # sender, for every concrete Vocabulary/Term subclass registered so
        # far (see icvoss/django-icv-taxonomy#40: bare post_save/pre_delete
        # registration disabled Django's fast-delete path for every model in
        # a consuming project, not just Vocabulary/Term).
        handlers._connect_vocabulary_term_handlers()

        # Conditionally bridge icv_tree.signals.node_moved to term_moved.
        # Skipped silently when icv-tree is not installed.
        handlers._connect_node_moved_handler()
