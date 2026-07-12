"""
Regression test: migrations must resolve the swappable model settings via
getattr() with the package defaults, so a consuming project that does not
declare ICV_TAXONOMY_VOCABULARY_MODEL / ICV_TAXONOMY_TERM_MODEL does not
crash on migrate or makemigrations.

The main test suite (tests/settings.py) sets MIGRATION_MODULES["icv_taxonomy"]
to None, so migrations never actually run there and this bug goes unnoticed.
This test runs Django management commands in a subprocess against
tests/settings_migrate_defaults.py, which enables real migrations and
deliberately omits both settings, to genuinely exercise the migration files.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SRC_DIR = TESTS_DIR.parent / "src"


def _run_django_command(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a Django management command in a subprocess against the
    migrate-defaults settings module, with a clean PYTHONPATH so it picks up
    the package sources and this settings module without inheriting the
    parent pytest process's already-configured settings.
    """
    env = dict(os.environ)
    env["DJANGO_SETTINGS_MODULE"] = "settings_migrate_defaults"
    env["PYTHONPATH"] = os.pathsep.join([str(SRC_DIR), str(TESTS_DIR)])

    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "django", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def test_migrate_succeeds_without_swappable_settings_declared() -> None:
    """`migrate` must succeed when neither ICV_TAXONOMY_VOCABULARY_MODEL nor
    ICV_TAXONOMY_TERM_MODEL is declared by the consuming project.
    """
    result = _run_django_command("migrate", "--noinput")

    assert result.returncode == 0, (
        f"migrate failed without ICV_TAXONOMY_*_MODEL declared:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "AttributeError" not in result.stderr


def test_makemigrations_check_reports_no_drift_without_swappable_settings() -> None:
    """`makemigrations --check --dry-run` must not crash with AttributeError
    when neither swappable setting is declared. The command may report
    legitimate drift (e.g. DEFAULT_AUTO_FIELD mismatches in icv_core),
    but should not raise AttributeError trying to resolve the model paths.
    """
    result = _run_django_command("makemigrations", "--check", "--dry-run")

    # The critical assertion: no AttributeError about missing settings.
    # Return code may be nonzero if there is actual drift, but that is
    # not the bug being tested here.
    assert "AttributeError" not in result.stderr, (
        f"makemigrations crashed with AttributeError:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
