"""
Regression test for issue #21 / BR-TAX-050: `Term.parent` must resolve
through `ICV_TAXONOMY_TERM_MODEL`, not TreeNode's `to="self"`, so that
`makemigrations --check` reports no drift when a consuming project swaps in
its own AbstractTerm subclass.

Before the fix, AbstractTerm inherited `parent` unmodified from
icv_tree.models.TreeNode. `to="self"` resolved directly to the swapped
subclass rather than through the swappable setting, so its deconstruct()
output permanently disagreed with the package's frozen migration state
(which targets settings.ICV_TAXONOMY_TERM_MODEL), producing a spurious
AlterField on `parent` purely from exercising the swap seam.

This test runs Django management commands in a subprocess against
tests/settings_migrate_swapped.py, which declares ICV_TAXONOMY_TERM_MODEL /
ICV_TAXONOMY_VOCABULARY_MODEL pointed at tests/appswap's own subclasses and
enables real migrations, to genuinely exercise the migration files rather
than the main suite's MIGRATION_MODULES=None shortcut (tests/settings.py).
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
    migrate-swapped settings module, with a clean PYTHONPATH so it picks up
    the package sources and this settings module without inheriting the
    parent pytest process's already-configured settings.
    """
    env = dict(os.environ)
    env["DJANGO_SETTINGS_MODULE"] = "settings_migrate_swapped"
    env["PYTHONPATH"] = os.pathsep.join([str(SRC_DIR), str(TESTS_DIR)])

    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "django", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def test_migrate_succeeds_with_term_model_swapped() -> None:
    """`migrate` must apply cleanly when ICV_TAXONOMY_TERM_MODEL points at a
    consuming project's own AbstractTerm subclass.
    """
    result = _run_django_command("migrate", "--noinput")

    assert result.returncode == 0, (
        f"migrate failed with ICV_TAXONOMY_TERM_MODEL swapped:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_makemigrations_check_reports_no_drift_with_term_model_swapped() -> None:
    """`makemigrations --check --dry-run` must report no changes when
    ICV_TAXONOMY_TERM_MODEL is swapped to a consuming project's own
    AbstractTerm subclass.

    This is the exact regression for issue #21: before the fix, this
    reported a spurious `AlterField` on `swapterm.parent` (mirroring the
    real-world `term.parent` drift) purely from exercising the swap, with no
    change to the consumer's own models.
    """
    result = _run_django_command("makemigrations", "--check", "--dry-run")

    assert result.returncode == 0, (
        f"makemigrations --check reported drift with ICV_TAXONOMY_TERM_MODEL "
        f"swapped (issue #21 regression):\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "No changes detected" in result.stdout
