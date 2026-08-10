"""Swapped Vocabulary/Term models for the icv-taxonomy consumer smoke-test
harness, exactly the shape a real consuming project builds: concrete
subclasses of AbstractVocabulary/AbstractTerm, registered via
ICV_TAXONOMY_VOCABULARY_MODEL / ICV_TAXONOMY_TERM_MODEL in settings.py.

ConsumerTerm is the load-bearing model here: AbstractTerm inherits
icv_tree.models.TreeNode, so this is what exercises the tree inheritance the
`makemigrations --check` gate exists to protect (a deconstruct()-visible
field change on TreeNode, e.g. path's help_text, forces an AlterField
migration here that this harness must detect).
"""

from __future__ import annotations

from icv_taxonomy.models import AbstractTerm, AbstractVocabulary


class ConsumerVocabulary(AbstractVocabulary):
    class Meta(AbstractVocabulary.Meta):
        abstract = False
        app_label = "consumer_app"


class ConsumerTerm(AbstractTerm):
    class Meta(AbstractTerm.Meta):
        abstract = False
        app_label = "consumer_app"
