"""
icv-taxonomy package settings.

All settings use the ICV_TAXONOMY_* prefix and are evaluated at call time via
get_setting() to respect pytest settings fixture overrides. Inside this
package, always call get_setting() (or one of the get_*_model() helpers)
inside function bodies, never a module-level constant.

For backwards compatibility, the six ICV_TAXONOMY_* names below are also
exposed as module attributes (e.g. ``conf.ICV_TAXONOMY_AUTO_SLUG``). These
are resolved lazily via module-level ``__getattr__`` (PEP 562): each access
reads the current Django setting rather than a value bound once at import
time. This means the module imports cleanly even when Django settings are
not yet configured, and each access reflects override_settings() or the
pytest settings fixture rather than a stale first-import value.
"""

from __future__ import annotations

from django.conf import settings


def get_setting(name: str, default):  # type: ignore[no-untyped-def]
    """Return the named ICV_TAXONOMY_* setting, falling back to default."""
    return getattr(settings, name, default)


def get_vocabulary_model():  # type: ignore[no-untyped-def]
    """Return the configured Vocabulary model class.

    Uses django.apps.apps.get_model() so swappable models are resolved at
    call time rather than import time.
    """
    from django.apps import apps

    model_string = get_setting("ICV_TAXONOMY_VOCABULARY_MODEL", "icv_taxonomy.Vocabulary")
    app_label, model_name = model_string.split(".")
    return apps.get_model(app_label, model_name)


def get_term_model():  # type: ignore[no-untyped-def]
    """Return the configured Term model class.

    Uses django.apps.apps.get_model() so swappable models are resolved at
    call time rather than import time.
    """
    from django.apps import apps

    model_string = get_setting("ICV_TAXONOMY_TERM_MODEL", "icv_taxonomy.Term")
    app_label, model_name = model_string.split(".")
    return apps.get_model(app_label, model_name)


def get_base_model():  # type: ignore[no-untyped-def]
    """Return the abstract model base every icv-taxonomy model inherits (ADR-052).

    Resolution order:

    1. ``ICV_TAXONOMY_BASE_MODEL``, this package only.
    2. ``ICV_BASE_MODEL``, the shared stack-wide base.
    3. ``icv_taxonomy._compat.BaseModel``, the bundled default.

    Uses ``import_string`` rather than ``apps.get_model``: the target is an
    ABSTRACT model, which has no app label or model name and so is not in
    the app registry.

    Called at class-definition time, unlike the other accessors here, since
    a base class must be resolved before the models that inherit it exist.
    That is why it reads settings inside the function body: the module must
    still import when Django is unconfigured.
    """
    from django.utils.module_loading import import_string

    path = (
        get_setting("ICV_TAXONOMY_BASE_MODEL", None)
        or get_setting("ICV_BASE_MODEL", None)
        or "icv_taxonomy._compat.BaseModel"
    )
    return import_string(path)


# ------------------------------------------------------------------
# Setting names, defaults, and their meaning.
#
# Each is exposed as a module attribute via __getattr__ below, and can
# always be read via get_setting(name, default) inside a function body.
# ------------------------------------------------------------------

_DEFAULTS: dict[str, object] = {
    # Model swapping: dotted model paths, AUTH_USER_MODEL-style.
    "ICV_TAXONOMY_VOCABULARY_MODEL": "icv_taxonomy.Vocabulary",
    "ICV_TAXONOMY_TERM_MODEL": "icv_taxonomy.Term",
    # Slug behaviour.
    # AUTO_SLUG: auto-generate slug from name when slug is blank on save (BR-TAX-043).
    "ICV_TAXONOMY_AUTO_SLUG": True,
    # SLUG_MAX_LENGTH: maximum length for auto-generated slugs.
    "ICV_TAXONOMY_SLUG_MAX_LENGTH": 255,
    # CASE_SENSITIVE_SLUGS: if False, slugs are lowercased on save (BR-TAX-034).
    # If True, case is preserved.
    "ICV_TAXONOMY_CASE_SENSITIVE_SLUGS": False,
    # Validation: enforce that flat vocabulary terms must be root-level (no
    # parent). Set to False to allow flat vocabularies to have nested terms
    # for migration compatibility.
    "ICV_TAXONOMY_ENFORCE_VOCABULARY_TYPE": True,
}


def __getattr__(name: str) -> object:  # PEP 562: lazy module attributes.
    """Resolve ICV_TAXONOMY_* module attributes at ACCESS time, not import time.

    Kept for backwards compatibility with code that reads e.g.
    ``icv_taxonomy.conf.ICV_TAXONOMY_AUTO_SLUG`` as a module attribute
    rather than calling get_setting(). Each access re-reads the current
    Django setting, so the value reflects override_settings() / the pytest
    settings fixture, and the module still imports when Django settings
    are not yet configured (the getattr() only runs when the attribute is
    actually accessed).
    """
    if name in _DEFAULTS:
        return get_setting(name, _DEFAULTS[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
