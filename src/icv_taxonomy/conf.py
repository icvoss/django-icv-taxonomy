"""
icv-taxonomy package settings.

All settings use the ICV_TAXONOMY_* prefix and are evaluated at call time via
get_setting() to respect pytest settings fixture overrides. Never import these
module-level constants into other modules — always call get_setting() inside
function bodies.
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
# Model swapping
# ------------------------------------------------------------------

# Dotted model path for the Vocabulary model. Supports swapping via
# AUTH_USER_MODEL-style indirection.
ICV_TAXONOMY_VOCABULARY_MODEL: str = getattr(settings, "ICV_TAXONOMY_VOCABULARY_MODEL", "icv_taxonomy.Vocabulary")

# Dotted model path for the Term model.
ICV_TAXONOMY_TERM_MODEL: str = getattr(settings, "ICV_TAXONOMY_TERM_MODEL", "icv_taxonomy.Term")

# ------------------------------------------------------------------
# Slug behaviour
# ------------------------------------------------------------------

# If True, auto-generate slug from name when slug is blank on save (BR-TAX-043).
ICV_TAXONOMY_AUTO_SLUG: bool = getattr(settings, "ICV_TAXONOMY_AUTO_SLUG", True)

# Maximum length for auto-generated slugs.
ICV_TAXONOMY_SLUG_MAX_LENGTH: int = getattr(settings, "ICV_TAXONOMY_SLUG_MAX_LENGTH", 255)

# If False, slugs are lowercased on save (BR-TAX-034). If True, case is preserved.
ICV_TAXONOMY_CASE_SENSITIVE_SLUGS: bool = getattr(settings, "ICV_TAXONOMY_CASE_SENSITIVE_SLUGS", False)

# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------

# If True, enforce that flat vocabulary terms must be root-level (no parent).
# Set to False to allow flat vocabularies to have nested terms for migration
# compatibility.
ICV_TAXONOMY_ENFORCE_VOCABULARY_TYPE: bool = getattr(settings, "ICV_TAXONOMY_ENFORCE_VOCABULARY_TYPE", True)
