"""
Regression test for icvoss/django-icv-taxonomy#36.

icv_taxonomy.conf used to bind six ICV_TAXONOMY_* names as module-level
constants via getattr(settings, ...) at IMPORT time. That contradicted the
module's own docstring (settings must be read at call time) and had two
consequences: the module could not be imported before Django settings were
configured, and the constants ignored override_settings()/the pytest
settings fixture because they were bound once, on first import.

This module proves both defects are fixed:

  * plain `import icv_taxonomy.conf` succeeds with Django settings
    unconfigured. This runs in a SUBPROCESS with DJANGO_SETTINGS_MODULE
    unset, because the parent pytest process already has settings
    configured (mirrors the subprocess idiom in test_migrations_defaults.py).
  * the ICV_TAXONOMY_* module attributes are resolved lazily (PEP 562
    module-level __getattr__): reading the same attribute twice, under two
    different override_settings() values, gives two different results.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.test import override_settings

TESTS_DIR = Path(__file__).resolve().parent
SRC_DIR = TESTS_DIR.parent / "src"


def _run_unconfigured_import(module: str) -> subprocess.CompletedProcess[str]:
    """Import `module` in a subprocess with no Django settings configured.

    DJANGO_SETTINGS_MODULE is deliberately absent from the child environment
    (rather than set to ""), and PYTHONPATH is scoped to just the package
    source, so the child process starts from a genuinely unconfigured
    Django, unlike the parent pytest process which already has
    tests.settings configured.
    """
    env = dict(os.environ)
    env.pop("DJANGO_SETTINGS_MODULE", None)
    env["PYTHONPATH"] = str(SRC_DIR)

    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", f"import {module}"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )


def test_conf_imports_with_settings_unconfigured() -> None:
    """`import icv_taxonomy.conf` must succeed with no Django settings
    configured. Before the PEP 562 __getattr__ fix, this raised
    ImproperlyConfigured at first module-level constant binding
    (ICV_TAXONOMY_VOCABULARY_MODEL): reverting src/icv_taxonomy/conf.py to
    its pre-fix form makes this assertion fail with a non-zero returncode
    and "ImproperlyConfigured" in stderr, which is the negative control.
    """
    result = _run_unconfigured_import("icv_taxonomy.conf")

    assert result.returncode == 0, (
        f"import icv_taxonomy.conf failed unconfigured:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "ImproperlyConfigured" not in result.stderr


def test_models_cannot_import_with_settings_unconfigured() -> None:
    """`import icv_taxonomy.models` legitimately CANNOT succeed unconfigured.

    models.py imports django.contrib.contenttypes.fields.GenericForeignKey
    (for AbstractTermAssociation), which imports
    django.contrib.contenttypes.models, which defines a concrete
    django.db.models.Model subclass (ContentType) at import time. Defining
    any Model subclass triggers Django's app-registry machinery
    (apps.get_containing_app_config), which requires settings.INSTALLED_APPS.
    This is a property of Django's contenttypes app, not a defect in this
    package's conf module, so the accurate assertion is that this import
    fails with ImproperlyConfigured, not that it succeeds.
    """
    result = _run_unconfigured_import("icv_taxonomy.models")

    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr


@pytest.mark.django_db
def test_module_attribute_is_lazy_and_reflects_override_settings() -> None:
    """Reading conf.ICV_TAXONOMY_AUTO_SLUG twice, under two different
    override_settings() values, must give two different results. A test
    that only checked the attribute exists, or read it once, would pass
    even against the pre-fix module-level constant (which is frozen at
    first import and does not track override_settings() at all) as long as
    the frozen value happened to match the default; this test is
    falsifiable because it requires the SAME attribute access to observe
    a change.
    """
    import icv_taxonomy.conf as conf

    with override_settings(ICV_TAXONOMY_AUTO_SLUG=True):
        first = conf.ICV_TAXONOMY_AUTO_SLUG

    with override_settings(ICV_TAXONOMY_AUTO_SLUG=False):
        second = conf.ICV_TAXONOMY_AUTO_SLUG

    assert first is True
    assert second is False
    assert first != second


@pytest.mark.django_db
def test_module_attribute_falls_back_to_documented_default() -> None:
    """With no override in effect, the module attribute resolves to the
    same default get_setting() would return.
    """
    import icv_taxonomy.conf as conf

    expected = conf.get_setting("ICV_TAXONOMY_SLUG_MAX_LENGTH", 255)
    assert expected == conf.ICV_TAXONOMY_SLUG_MAX_LENGTH


def test_unknown_module_attribute_still_raises_attributeerror() -> None:
    """__getattr__ must not swallow lookups for names it does not own."""
    import icv_taxonomy.conf as conf

    with pytest.raises(AttributeError):
        conf.NOT_A_REAL_SETTING  # noqa: B018
