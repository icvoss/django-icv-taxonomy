"""Tests for per-sender connection of the Vocabulary/Term signal handlers.

Regression coverage for icvoss/django-icv-taxonomy#40: the four handlers in
handlers.py used to connect with no sender, attaching to every model in a
consuming project. Django's Collector.can_fast_delete() returns False for
any model carrying a pre_delete/post_delete listener, so this silently
removed the fast-delete path (a single DELETE ... WHERE) from every
queryset .delete() in a consumer project, not just Vocabulary/Term deletes.
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from django.db.models.deletion import Collector
from django.db.models.signals import post_delete, post_save, pre_delete

# ---------------------------------------------------------------------------
# Receivers are NOT connected to unrelated models
# ---------------------------------------------------------------------------


class TestHandlersNotConnectedToUnrelatedModels:
    """AC-40: the taxonomy handlers must not attach to non-Vocabulary/Term models."""

    def test_post_save_has_no_listeners_for_unrelated_model(self):
        """post_save.has_listeners() is False for a model the package does not own."""
        from taxonomy_testapp.models import Article

        assert post_save.has_listeners(Article) is False

    def test_pre_delete_has_no_listeners_for_unrelated_model(self):
        """pre_delete.has_listeners() is False for a model the package does not own.

        This is the load-bearing assertion for #40: pre_delete listeners are
        what disable Django's fast-delete path via Collector.can_fast_delete().
        """
        from taxonomy_testapp.models import Article, Product

        assert pre_delete.has_listeners(Article) is False
        assert pre_delete.has_listeners(Product) is False

    def test_scope_model_has_no_taxonomy_listeners(self):
        """A consumer's own unrelated model (Scope) is not wired to taxonomy handlers.

        Scope has an incoming FK from ScopedVocabulary, so it is not itself
        fast-deletable, but that must come from its own relations, never from
        a taxonomy handler attaching to it directly.
        """
        from taxonomy_testapp.models import Scope

        from icv_taxonomy import handlers

        sync_receivers, _async_receivers = pre_delete._live_receivers(Scope)
        assert handlers.handle_vocabulary_pre_delete not in sync_receivers
        assert handlers.handle_term_pre_delete not in sync_receivers


# ---------------------------------------------------------------------------
# Receivers ARE connected for Vocabulary/Term models, and still fire
# ---------------------------------------------------------------------------


class TestHandlersConnectedToVocabularyAndTermModels:
    """AC-40: the taxonomy handlers must still attach to Vocabulary/Term models."""

    def test_post_save_has_listeners_for_vocabulary_model(self):
        from icv_taxonomy.conf import get_vocabulary_model

        Vocabulary = get_vocabulary_model()
        assert post_save.has_listeners(Vocabulary) is True

    def test_pre_delete_has_listeners_for_vocabulary_model(self):
        from icv_taxonomy.conf import get_vocabulary_model

        Vocabulary = get_vocabulary_model()
        assert pre_delete.has_listeners(Vocabulary) is True

    def test_post_save_has_listeners_for_term_model(self):
        from icv_taxonomy.conf import get_term_model

        Term = get_term_model()
        assert post_save.has_listeners(Term) is True

    def test_pre_delete_has_listeners_for_term_model(self):
        from icv_taxonomy.conf import get_term_model

        Term = get_term_model()
        assert pre_delete.has_listeners(Term) is True

    def test_post_save_has_listeners_for_scoped_vocabulary_subclass(self):
        """A concrete AbstractVocabulary subclass (not the default model) is also connected.

        ScopedVocabulary is a real subclass registered in taxonomy_testapp,
        proving the fix connects every concrete subclass, not just the
        model resolved by ICV_TAXONOMY_VOCABULARY_MODEL.
        """
        from taxonomy_testapp.models import ScopedVocabulary

        assert post_save.has_listeners(ScopedVocabulary) is True
        assert pre_delete.has_listeners(ScopedVocabulary) is True

    @pytest.mark.django_db
    def test_vocabulary_created_still_fires(self, db):
        """Existing signal behaviour survives the per-sender connection change."""
        from icv_taxonomy.services import create_vocabulary
        from icv_taxonomy.signals import vocabulary_created

        calls = []

        def handler(**kwargs) -> None:
            calls.append(kwargs)

        vocabulary_created.connect(handler, weak=False)
        try:
            vocab = create_vocabulary(name="Reconnect Check", slug="reconnect-check")
        finally:
            vocabulary_created.disconnect(handler)

        assert len(calls) == 1
        assert calls[0]["vocabulary"].pk == vocab.pk

    @pytest.mark.django_db
    def test_term_deleted_still_fires(self, db, flat_vocabulary):
        """Existing pre_delete signal behaviour survives the per-sender connection change."""
        from icv_taxonomy.services import create_term, delete_term
        from icv_taxonomy.signals import term_deleted

        term = create_term(vocabulary=flat_vocabulary, name="Reconnect Deleted Term")
        term_pk = term.pk

        captured = []

        def handler(term, **kwargs) -> None:
            captured.append(term.pk)

        term_deleted.connect(handler, weak=False)
        try:
            delete_term(term)
        finally:
            term_deleted.disconnect(handler)

        assert captured == [term_pk]


# ---------------------------------------------------------------------------
# Fast-delete regression: an unrelated, cascade-free model regains
# Collector.can_fast_delete()
# ---------------------------------------------------------------------------


@contextmanager
def _icv_tree_post_delete_disconnected():
    """Temporarily disconnect icv_tree's own senderless post_delete receiver.

    icv_tree is a hard INSTALLED_APPS dependency in this fixture and connects
    its own post_delete handler senderless (bare ``@receiver(post_delete)``
    in icv_tree.handlers), filtering by sender internally rather than at
    connect time (the same anti-pattern #40 fixed in this package, present
    upstream in django-icv-tree itself; a candidate defect there, out of
    scope here). Collector.can_fast_delete() only checks connection
    presence via has_listeners(), never invokes the handler body, so
    icv_tree's own documented skip_tree_signals() (which only gates the
    handler body) cannot neutralise it: the receiver must be disconnected
    outright for the duration of the assertion, and reconnected after, so
    these tests are sensitive only to icv-taxonomy's own listeners, which is
    what #40 actually fixed.
    """
    from icv_tree.handlers import handle_post_delete

    post_delete.disconnect(handle_post_delete)
    try:
        yield
    finally:
        post_delete.connect(handle_post_delete)


@pytest.mark.django_db
class TestFastDeleteRegainedForUnrelatedModels:
    """AC-40: a cascade-free consumer model regains Django's fast-delete path.

    Article and Product in taxonomy_testapp have no incoming ForeignKey from
    any model (TermAssociation links via GenericForeignKey, which the
    deletion Collector does not walk), so a signal listener FROM THIS
    PACKAGE was the only thing #40's fix controls that could block
    can_fast_delete() for them. See _icv_tree_post_delete_disconnected()
    above for why icv_tree's own senderless post_delete receiver must be
    disconnected for these assertions to be faithful. TestHandlersNotConnectedToUnrelatedModels
    above already proves icv-taxonomy attaches no pre_delete/post_delete
    listener to Article/Product at all.
    """

    def test_article_regains_fast_delete(self, db):
        from taxonomy_testapp.models import Article

        Article.objects.create(title="Fast Delete Candidate")

        collector = Collector(using="default")
        with _icv_tree_post_delete_disconnected():
            assert collector.can_fast_delete(Article.objects.all()) is True

    def test_product_regains_fast_delete(self, db):
        from taxonomy_testapp.models import Product

        Product.objects.create(name="Fast Delete Candidate")

        collector = Collector(using="default")
        with _icv_tree_post_delete_disconnected():
            assert collector.can_fast_delete(Product.objects.all()) is True

    def test_fast_delete_is_false_when_a_pre_delete_listener_is_added(self, db):
        """Control: proves the assertions above are sensitive to a real listener,
        not vacuously true regardless of connection state.
        """
        from taxonomy_testapp.models import Article

        Article.objects.create(title="Control Candidate")

        def noop(**kwargs) -> None:
            return None

        pre_delete.connect(noop, sender=Article, dispatch_uid="test.control.noop", weak=False)
        try:
            collector = Collector(using="default")
            with _icv_tree_post_delete_disconnected():
                assert collector.can_fast_delete(Article.objects.all()) is False
        finally:
            pre_delete.disconnect(sender=Article, dispatch_uid="test.control.noop")

        # And it is restored once the control listener is removed.
        collector = Collector(using="default")
        with _icv_tree_post_delete_disconnected():
            assert collector.can_fast_delete(Article.objects.all()) is True

    def test_term_model_itself_is_not_fast_deletable(self, db, flat_vocabulary):
        """Term still carries its own pre_delete listener (by design): term_deleted
        must keep firing per row for clear_vocabulary()/bulk deletes (see
        TestClearVocabularySignals in test_signals.py). This is the intended,
        narrowed cost: only Term/Vocabulary pay it, not every consumer model.
        """
        from icv_taxonomy.conf import get_term_model

        Term = get_term_model()
        collector = Collector(using="default")
        assert collector.can_fast_delete(Term.objects.all()) is False


# ---------------------------------------------------------------------------
# dispatch_uid guards against double connection
# ---------------------------------------------------------------------------


class TestDoubleReadyDoesNotDoubleConnect:
    """AC-40: calling the connect functions twice must not register a handler twice."""

    def test_connect_vocabulary_term_handlers_is_idempotent(self):
        from icv_taxonomy import handlers
        from icv_taxonomy.conf import get_vocabulary_model

        Vocabulary = get_vocabulary_model()
        sync_before, async_before = post_save._live_receivers(Vocabulary)

        # Simulate a second ready() call.
        handlers._connect_vocabulary_term_handlers()

        sync_after, async_after = post_save._live_receivers(Vocabulary)
        assert len(sync_after) == len(sync_before)
        assert len(async_after) == len(async_before)
