"""
System checks for icv-taxonomy.

Registered automatically by IcvTaxonomyConfig.ready() via import.
"""

from __future__ import annotations

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
