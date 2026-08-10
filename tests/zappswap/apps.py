"""AppConfig for the swappable-model migration regression test (issues #21,
#22).

Named "zappswap" deliberately: it sorts AFTER "icv_taxonomy" alphabetically,
so Django's default app-processing order runs icv_taxonomy's migrations
first. That is the exact ordering issue #22's swappable_dependency edges
must correct: without them, `migrate` crashes because icv_taxonomy's
migrations run before this app creates the models they FK to.
"""

from __future__ import annotations

from django.apps import AppConfig


class SwapAppConfig(AppConfig):
    name = "zappswap"
    label = "zappswap"
    verbose_name = "icv-taxonomy swappable-model regression app"
    default_auto_field = "django.db.models.BigAutoField"
