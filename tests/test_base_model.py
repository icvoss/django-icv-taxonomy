"""
ADR-052: the model base resolves from a settings string, not from whether
django-icv-core happens to be importable.

Two things need proving, and they fail in different places:

1. Resolution itself (get_base_model precedence, the E003 system check).
   Cheap, runs in-process.

2. BYTE-COMPATIBILITY of the bundled default against the package's own
   frozen migrations. This is the one that matters, because it fails in the
   CONSUMER rather than in package CI: a kwarg dropped from
   _compat.BaseModel puts it below the frozen migration state, and the
   consumer's next makemigrations --check emits a compensating AlterField
   that DROPS a live index on created_at. Asserted here against the
   migration files directly, so the suite catches it without needing
   django-icv-core installed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from django.core.checks import Error
from django.db import models
from django.test import override_settings

from icv_taxonomy._compat import BaseModel
from icv_taxonomy.checks import check_base_model_is_abstract
from icv_taxonomy.conf import get_base_model

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
MIGRATIONS_DIR = SRC_DIR / "icv_taxonomy" / "migrations"


# ------------------------------------------------------------------
# Resolution order
# ------------------------------------------------------------------


def test_defaults_to_bundled_compat_base():
    """With neither setting set, the bundled _compat.BaseModel is used."""
    assert get_base_model() is BaseModel


@override_settings(ICV_BASE_MODEL="icv_taxonomy._compat.BaseModel")
def test_shared_setting_is_honoured():
    """ICV_BASE_MODEL is read when the package-specific setting is unset."""
    assert get_base_model() is BaseModel


class _AltBase(models.Model):
    class Meta:
        abstract = True


@override_settings(
    ICV_TAXONOMY_BASE_MODEL="tests.test_base_model._AltBase",
    ICV_BASE_MODEL="icv_taxonomy._compat.BaseModel",
)
def test_package_setting_wins_over_shared_setting():
    """ICV_TAXONOMY_BASE_MODEL takes precedence over ICV_BASE_MODEL.

    Both are set to DIFFERENT values deliberately: if precedence were
    reversed, or if either were ignored, this returns the wrong class.
    """
    assert get_base_model() is _AltBase


# ------------------------------------------------------------------
# The E003 system check
# ------------------------------------------------------------------


def test_check_passes_on_the_default_base():
    assert check_base_model_is_abstract(None) == []


@override_settings(ICV_TAXONOMY_BASE_MODEL="icv_taxonomy._compat.NoSuchThing")
def test_check_flags_an_unimportable_path():
    errors = check_base_model_is_abstract(None)
    assert [e.id for e in errors] == ["icv_taxonomy.E003"]
    assert isinstance(errors[0], Error)


@override_settings(ICV_TAXONOMY_BASE_MODEL="icv_taxonomy.conf.get_setting")
def test_check_flags_a_non_model():
    errors = check_base_model_is_abstract(None)
    assert [e.id for e in errors] == ["icv_taxonomy.E003"]
    assert "not a Django model" in errors[0].msg


@override_settings(ICV_TAXONOMY_BASE_MODEL="icv_taxonomy.models.Vocabulary")
def test_check_flags_a_concrete_model():
    """A concrete base is the failure worth its own check: without it, the
    error surfaces deep in Django's model machinery without naming the
    setting responsible.
    """
    errors = check_base_model_is_abstract(None)
    assert [e.id for e in errors] == ["icv_taxonomy.E003"]
    assert "CONCRETE" in errors[0].msg


# ------------------------------------------------------------------
# Byte-compatibility against the frozen migrations
# ------------------------------------------------------------------


def _frozen_field_kwargs(migration_filename: str, model_name: str, field_name: str) -> dict[str, str]:
    """Return the kwargs a migration freezes for one field, parsed via AST.

    AST rather than grep: a docstring or comment mentioning a field reads
    identically to a live definition under a text search.
    """
    tree = ast.parse((MIGRATIONS_DIR / migration_filename).read_text())

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "CreateModel"):
            continue
        kw = {k.arg: k.value for k in node.keywords}
        name_node = kw.get("name")
        if not (isinstance(name_node, ast.Constant) and name_node.value == model_name):
            continue

        fields_node = kw.get("fields")
        assert isinstance(fields_node, ast.List), f"{model_name} has no fields list"

        for element in fields_node.elts:
            assert isinstance(element, ast.Tuple) and len(element.elts) == 2
            fname, fcall = element.elts
            if not (isinstance(fname, ast.Constant) and fname.value == field_name):
                continue
            assert isinstance(fcall, ast.Call), f"{field_name} is not a field call"
            return {k.arg: ast.unparse(k.value) for k in fcall.keywords if k.arg is not None}

    raise AssertionError(f"{model_name}.{field_name} not found in {migration_filename}")


# Both the pre-squash chain and the squashed migration freeze the base
# fields, so both are checked: a consumer may be on either.
MIGRATION_FILES = [
    "0001_initial.py",
    "0001_squashed_0003_alter_term_vocabulary_alter_termassociation_term_and_more.py",
]

BASE_MODELS = ["Vocabulary", "Term"]


@pytest.mark.parametrize("migration_filename", MIGRATION_FILES)
@pytest.mark.parametrize("model_name", BASE_MODELS)
def test_compat_base_matches_frozen_migration_state(migration_filename, model_name):
    """Every kwarg the live _compat base declares must match what the
    migrations froze, for each field the base contributes.

    If this fails, the bundled base has drifted from the package's own
    migration state, and every consumer gets a spurious AlterField on their
    next makemigrations --check. For created_at that AlterField DROPS a
    live database index.
    """
    for field_name, expected in (
        ("id", {"default": "uuid.uuid4", "editable": "False", "primary_key": "True"}),
        ("created_at", {"auto_now_add": "True", "db_index": "True"}),
        ("updated_at", {"auto_now": "True"}),
    ):
        frozen = _frozen_field_kwargs(migration_filename, model_name, field_name)

        # Guard against a vacuous pass: an empty parse would satisfy every
        # subset assertion below.
        assert frozen, f"parsed no kwargs for {model_name}.{field_name}"

        for kwarg, value in expected.items():
            assert frozen.get(kwarg) == value, (
                f"{migration_filename}: {model_name}.{field_name} freezes "
                f"{kwarg}={frozen.get(kwarg)!r}, expected {value!r}"
            )

        live_field = BaseModel._meta.get_field(field_name)

        if "db_index" in expected:
            assert live_field.db_index is True, (
                f"_compat.BaseModel.{field_name} lost db_index=True. The frozen "
                f"migrations carry it, so this drop emits an AlterField that "
                f"drops a live index in every consumer."
            )

        # verbose_name is in deconstruct() too, so it is load-bearing even
        # though the migrations render it positionally.
        assert str(live_field.verbose_name), f"_compat.BaseModel.{field_name} lost its verbose_name"


def test_compat_base_declares_no_meta_ordering():
    """ADR-066: an ordering on a shared base defeats values()/distinct() in
    every inheriting model.
    """
    assert BaseModel._meta.ordering == []


def test_compat_base_is_abstract_and_core_free():
    """The bundled default must not reference icv-core in any way (ADR-052)."""
    assert BaseModel._meta.abstract is True

    source = (SRC_DIR / "icv_taxonomy" / "_compat.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("icv_core"), "_compat imports icv_core"
        elif isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith("icv_core"), "_compat imports icv_core"


def test_models_no_longer_guard_import_icv_core():
    """The ADR-007 try/except icv_core import is gone from models.py.

    Asserted on the import graph via AST, not on a text search: a docstring
    mentioning icv_core reads identically to a live import under grep.
    """
    tree = ast.parse((SRC_DIR / "icv_taxonomy" / "models.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith("icv_core"), (
                "models.py still imports icv_core; ADR-052 resolves the base from settings"
            )
