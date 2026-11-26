"""
System checks for icv-taxonomy.

Registered automatically by IcvTaxonomyConfig.ready() via import.
"""

from __future__ import annotations

import logging

from django.core.checks import Error, register


@register()
def check_vocabulary_model(app_configs, **kwargs):  # type: ignore[no-untyped-def]
    """Validate ICV_TAXONOMY_VOCABULARY_MODEL points to a valid model (icv_taxonomy.E001)."""
    from .conf import get_setting

    errors = []
    model_string = get_setting("ICV_TAXONOMY_VOCABULARY_MODEL", "icv_taxonomy.Vocabulary")

    if not isinstance(model_string, str) or "." not in model_string:
        errors.append(
            Error(
                f"ICV_TAXONOMY_VOCABULARY_MODEL must be a dotted 'app_label.ModelName' string. Got: {model_string!r}",
                id="icv_taxonomy.E001",
            )
        )

    return errors


@register()
def check_term_model(app_configs, **kwargs):  # type: ignore[no-untyped-def]
    """Validate ICV_TAXONOMY_TERM_MODEL points to a valid model (icv_taxonomy.E002)."""
    from .conf import get_setting

    errors = []
    model_string = get_setting("ICV_TAXONOMY_TERM_MODEL", "icv_taxonomy.Term")

    if not isinstance(model_string, str) or "." not in model_string:
        errors.append(
            Error(
                f"ICV_TAXONOMY_TERM_MODEL must be a dotted 'app_label.ModelName' string. Got: {model_string!r}",
                id="icv_taxonomy.E002",
            )
        )

    return errors


@register()
def check_base_model_is_abstract(app_configs, **kwargs):  # type: ignore[no-untyped-def]
    """Validate the ADR-052 model base resolves to an abstract model (icv_taxonomy.E003).

    Three ways this goes wrong, all reported under one id: the setting names
    something unimportable, something that is not a Django model, or a
    CONCRETE model. The last is the one worth a check of its own: a concrete
    base fails deep inside Django's model machinery with an error that does
    not name the setting that caused it.
    """
    import inspect

    from .conf import get_base_model

    hint_setting = "ICV_TAXONOMY_BASE_MODEL/ICV_BASE_MODEL"

    try:
        base = get_base_model()
    except Exception as exc:
        return [
            Error(
                f"{hint_setting} does not resolve to an importable class: {exc}",
                hint=(
                    "Set ICV_TAXONOMY_BASE_MODEL or ICV_BASE_MODEL to a dotted path "
                    "('module.path.ClassName') naming an abstract Django model, or leave both "
                    "unset to use the bundled icv_taxonomy._compat.BaseModel default."
                ),
                id="icv_taxonomy.E003",
            )
        ]

    if not (inspect.isclass(base) and hasattr(base, "_meta")):
        return [
            Error(
                f"{hint_setting} resolves to {base!r}, which is not a Django model class.",
                hint="Point the setting at a Django model class, not a plain class, function, or instance.",
                id="icv_taxonomy.E003",
            )
        ]

    if not base._meta.abstract:
        return [
            Error(
                f"{hint_setting} resolves to {base.__name__!r}, which is a CONCRETE model (Meta.abstract is not True).",
                hint=(
                    "The base every icv-taxonomy model inherits must be abstract: it has no "
                    "app-label or model-name of its own and cannot be a swappable concrete model "
                    "(ADR-052 section 2). Point the setting at an abstract model, for example "
                    "icv_core.models.BaseModel."
                ),
                obj=base,
                id="icv_taxonomy.E003",
            )
        ]

    return []


E004_ID = "icv_taxonomy.E004"
_PACKAGE_LOGGER_NAME = "icv_taxonomy"


def _has_reachable_handler(logger_name: str) -> bool:
    """Return whether a handler is attached anywhere in ``logger_name``'s
    hierarchy that a record from it would actually reach, walking ancestors
    while ``propagate`` is true. ``logging.lastResort`` (the module-level
    fallback that stderr-prints WARNING+ when nothing else is configured) is
    not a configured handler and is ignored, per ADR-101 decision 3: it
    exists precisely to be invisible/unmanaged, not a substitute for a real
    handler the consumer chose.
    """
    logger = logging.getLogger(logger_name)

    current: logging.Logger | None = logger
    while current is not None:
        if any(handler is not logging.lastResort for handler in current.handlers):
            return True
        if not current.propagate:
            return False
        current = current.parent

    return False


@register()
def check_logging_handler_configured(app_configs, **kwargs):  # type: ignore[no-untyped-def]
    """Fail with an Error when no handler reaches the icv_taxonomy logger hierarchy (icv_taxonomy.E004).

    ADR-101 decision 3 and docs/STANDARDS.md section 15: a package that
    emits through logging ships a boot-time check confirming the
    consumer's LOGGING configuration actually routes it somewhere, and
    it fails as an Error, not a Warning. The failures this package logs
    (a `get_terms` or related template tag failing silently, and admin
    warnings) rely on this.
    """
    if _has_reachable_handler(_PACKAGE_LOGGER_NAME):
        return []

    logger_names = f"'{_PACKAGE_LOGGER_NAME}'"
    return [
        Error(
            "No logging handler is configured to receive records from the "
            f"{logger_names} logger (or any of its ancestors while "
            "propagate=True), so failures icv-taxonomy logs will be invisible.",
            hint=(
                "Add a handler for the 'icv_taxonomy' logger (or the root logger, "
                "if it propagates) in your LOGGING setting, e.g. "
                "LOGGING['loggers']['icv_taxonomy'] = {'handlers': [...], "
                "'level': 'WARNING', 'propagate': True}."
            ),
            id=E004_ID,
        )
    ]
