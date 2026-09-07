"""Signal handlers for icv-taxonomy.

handle_vocabulary_post_save: emits vocabulary_created on new Vocabulary instances.
handle_vocabulary_pre_delete: emits vocabulary_deleted before a Vocabulary is removed.
handle_term_post_save: emits term_created on new Term instances.
handle_term_pre_delete: emits term_deleted before a Term is removed.
handle_node_moved: bridges icv_tree.signals.node_moved to term_moved when the
    moved node is a Term subclass.

The Vocabulary and Term handlers are connected per sender, never bare, so
that unrelated consumer models keep Django's fast-delete path (see
icvoss/django-icv-taxonomy#40). Connection happens twice, deliberately:

- ``_connect_vocabulary_term_handlers()`` walks ``apps.get_models()`` from
  ``IcvTaxonomyConfig.ready()``, connecting every concrete Vocabulary/Term
  subclass that exists once the app registry is populated.
- ``_connect_handlers_for_new_model()`` listens on ``class_prepared`` so a
  model defined AFTER ``ready()`` (a test local subclass, a dynamically
  built model) still gets wired. This mirrors the ``class_prepared`` idiom
  already used in ``models.py`` for the same "late defined subclass"
  problem.

Both paths use ``dispatch_uid`` per sender, so re-running either (a second
``ready()`` under some test runners, a duplicate ``class_prepared`` fire)
never double-connects a handler.
"""

from __future__ import annotations

from django.db.models.signals import class_prepared, post_save, pre_delete

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_vocabulary_subclass(sender) -> bool:  # type: ignore[no-untyped-def]
    """Return True if sender is a concrete (non-abstract) AbstractVocabulary subclass.

    Checked against the abstract base, not get_vocabulary_model() (the
    swappable resolved default): a consumer may define more than one
    concrete AbstractVocabulary subclass alongside the default Vocabulary
    model (see taxonomy_testapp.models.ScopedVocabulary), and every one of
    them needs its post_save/pre_delete handlers connected, not just the
    model resolved by ICV_TAXONOMY_VOCABULARY_MODEL. Mirrors the predicate
    models.py already uses in _attach_vocabulary_uniqueness.
    """
    from .models import AbstractVocabulary

    return isinstance(sender, type) and issubclass(sender, AbstractVocabulary) and not sender._meta.abstract


def _is_term_subclass(sender) -> bool:  # type: ignore[no-untyped-def]
    """Return True if sender is a concrete (non-abstract) AbstractTerm subclass.

    Checked against the abstract base, not get_term_model() (the swappable
    resolved default), for the same reason as _is_vocabulary_subclass above:
    every concrete AbstractTerm subclass needs handlers connected, not just
    the one resolved by ICV_TAXONOMY_TERM_MODEL.
    """
    from .models import AbstractTerm

    return isinstance(sender, type) and issubclass(sender, AbstractTerm) and not sender._meta.abstract


# ---------------------------------------------------------------------------
# Vocabulary handlers
# ---------------------------------------------------------------------------


def handle_vocabulary_post_save(  # type: ignore[no-untyped-def]
    sender, instance, created, **kwargs
) -> None:
    """Emit vocabulary_created when a new Vocabulary instance is saved.

    Ignores updates (created=False) and non-Vocabulary senders.
    """
    if not _is_vocabulary_subclass(sender):
        return
    if not created:
        return

    from .signals import vocabulary_created

    vocabulary_created.send(sender=sender, vocabulary=instance)


def handle_vocabulary_pre_delete(  # type: ignore[no-untyped-def]
    sender, instance, **kwargs
) -> None:
    """Emit vocabulary_deleted before a Vocabulary instance is removed.

    Fires pre-delete so handlers can still inspect the vocabulary's terms
    before the CASCADE removes them.
    """
    if not _is_vocabulary_subclass(sender):
        return

    from .signals import vocabulary_deleted

    vocabulary_deleted.send(sender=sender, vocabulary=instance)


# ---------------------------------------------------------------------------
# Term handlers
# ---------------------------------------------------------------------------


def handle_term_post_save(  # type: ignore[no-untyped-def]
    sender, instance, created, **kwargs
) -> None:
    """Emit term_created when a new Term instance is saved.

    Ignores updates (created=False) and non-Term senders.
    """
    if not _is_term_subclass(sender):
        return
    if not created:
        return

    from .signals import term_created

    term_created.send(sender=sender, term=instance, vocabulary=instance.vocabulary)


def handle_term_pre_delete(  # type: ignore[no-untyped-def]
    sender, instance, **kwargs
) -> None:
    """Emit term_deleted before a Term instance is removed.

    Fires pre-delete so handlers can still inspect the term's associations
    (e.g. TermAssociation rows) before the CASCADE removes them.
    """
    if not _is_term_subclass(sender):
        return

    from .signals import term_deleted

    term_deleted.send(sender=sender, term=instance, vocabulary=instance.vocabulary)


# ---------------------------------------------------------------------------
# Per-sender connection (icvoss/django-icv-taxonomy#40)
# ---------------------------------------------------------------------------

# Handlers keyed by the signal they connect to and the predicate that
# decides whether a given model is one of theirs. Shared by both connection
# paths below so the two never drift apart.
_VOCABULARY_RECEIVERS = (
    (post_save, handle_vocabulary_post_save, "handle_vocabulary_post_save"),
    (pre_delete, handle_vocabulary_pre_delete, "handle_vocabulary_pre_delete"),
)
_TERM_RECEIVERS = (
    (post_save, handle_term_post_save, "handle_term_post_save"),
    (pre_delete, handle_term_pre_delete, "handle_term_pre_delete"),
)


def _connect_for_model(model) -> None:  # type: ignore[no-untyped-def]
    """Connect the Vocabulary/Term handlers for a single concrete model.

    A no-op for any model that is neither a concrete Vocabulary subclass nor
    a concrete Term subclass. Uses a dispatch_uid keyed on the handler name
    and the model, so calling this more than once for the same model (a
    second ready(), a duplicate class_prepared fire) never double-connects.
    """
    if _is_vocabulary_subclass(model):
        for signal, handler, name in _VOCABULARY_RECEIVERS:
            signal.connect(
                handler,
                sender=model,
                dispatch_uid=f"icv_taxonomy.handlers.{name}.{model._meta.label}",
            )
    if _is_term_subclass(model):
        for signal, handler, name in _TERM_RECEIVERS:
            signal.connect(
                handler,
                sender=model,
                dispatch_uid=f"icv_taxonomy.handlers.{name}.{model._meta.label}",
            )


def _connect_vocabulary_term_handlers() -> None:
    """Connect the Vocabulary/Term handlers for every model already registered.

    Called from IcvTaxonomyConfig.ready(). Walks apps.get_models(), which is
    safe once the app registry is populated, and connects each handler with
    an explicit sender rather than the bare post_save/pre_delete registration
    this replaces. Bare registration attached to every model in a consuming
    project, which disables Django's fast-delete path for all of them: see
    #40 for the measured impact.

    Skips abstract models implicitly, since apps.get_models() never returns
    them. Resolves subclasses through _is_vocabulary_subclass /
    _is_term_subclass, which read the swappable model via
    get_vocabulary_model() / get_term_model(), so a consumer's swapped-in
    model and any further subclass of it are both connected correctly.

    Models defined after this call (a test-local model, a model built
    dynamically at runtime) are not covered here; see
    _connect_handlers_for_new_model() below for that case.
    """
    from django.apps import apps

    for model in apps.get_models():
        _connect_for_model(model)


def _connect_handlers_for_new_model(sender, **kwargs) -> None:  # type: ignore[no-untyped-def]
    """class_prepared receiver: wire a model defined after ready() has run.

    apps.get_models() in _connect_vocabulary_term_handlers() only sees
    models that exist at ready() time. A model defined afterwards, such as a
    test-local subclass or one built dynamically, would otherwise never get
    connected. This listens on class_prepared instead, the same idiom
    models.py already uses for _attach_vocabulary_uniqueness.

    Guarded on apps.models_ready: class_prepared also fires for every model
    in the project during Django's own app-loading pass, well before that
    point, and _is_vocabulary_subclass / _is_term_subclass call
    get_vocabulary_model() / get_term_model(), which call apps.get_model()
    with require_ready=True and raise AppRegistryNotReady if called too
    early. Models prepared during app loading are already covered by
    _connect_vocabulary_term_handlers() once ready() runs, so skipping them
    here loses nothing.
    """
    from django.apps import apps

    if not apps.models_ready:
        return
    _connect_for_model(sender)


class_prepared.connect(_connect_handlers_for_new_model)


# ---------------------------------------------------------------------------
# icv-tree bridge: node_moved to term_moved
# ---------------------------------------------------------------------------


def _connect_node_moved_handler() -> None:
    """Connect handle_node_moved to icv_tree.signals.node_moved if icv-tree is installed.

    Called from IcvTaxonomyConfig.ready(). Wrapped in a function so that the
    import of icv_tree.signals is deferred until Django's app registry is ready,
    and so the handler is silently skipped when icv-tree is not installed (e.g.
    in consuming projects that use flat vocabularies only).
    """
    try:
        from icv_tree import signals as tree_signals
    except ImportError:
        # icv-tree is not installed — term_moved will only be emitted by the
        # merge service directly; the tree bridge is not available.
        return

    tree_signals.node_moved.connect(
        handle_node_moved,
        dispatch_uid="icv_taxonomy.handlers.handle_node_moved",
    )


def handle_node_moved(  # type: ignore[no-untyped-def]
    sender, instance, old_parent, new_parent, old_path, **kwargs
) -> None:
    """Bridge icv_tree.signals.node_moved to icv_taxonomy.signals.term_moved.

    Only emits term_moved when the moved node's model is a concrete Term
    subclass. Passes taxonomy-specific context (term, old_parent, new_parent,
    old_path) rather than the raw tree fields.

    Connected via _connect_node_moved_handler() in IcvTaxonomyConfig.ready().
    """
    if not _is_term_subclass(sender):
        return

    from .signals import term_moved

    term_moved.send(
        sender=sender,
        term=instance,
        old_parent=old_parent,
        new_parent=new_parent,
        old_path=old_path,
    )
