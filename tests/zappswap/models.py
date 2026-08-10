"""Swapped Term/Vocabulary models for the swappable-model migration regression
test (issues #21, #22; BR-TAX-050).

Minimal concrete subclasses of AbstractVocabulary/AbstractTerm, the shape a
real consuming project builds when it sets ICV_TAXONOMY_VOCABULARY_MODEL /
ICV_TAXONOMY_TERM_MODEL. AppSwapTerm is the load-bearing model: AbstractTerm
inherits icv_tree.models.TreeNode, so this exercises the "self" vs swappable
FK-target resolution on `parent` that BR-TAX-050 requires.

The app_label "zappswap" is deliberate: it sorts AFTER "icv_taxonomy"
alphabetically, so a missing swappable_dependency edge in icv_taxonomy's
migrations (issue #22) surfaces as a genuine `migrate` failure instead of
hiding behind Django's default app-processing order.
"""

from __future__ import annotations

from icv_taxonomy.models import AbstractTerm, AbstractVocabulary


class AppSwapVocabulary(AbstractVocabulary):
    class Meta(AbstractVocabulary.Meta):
        abstract = False
        app_label = "zappswap"


class AppSwapTerm(AbstractTerm):
    class Meta(AbstractTerm.Meta):
        abstract = False
        app_label = "zappswap"
