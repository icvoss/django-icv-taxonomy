"""
Regression tests for issue #21 (BR-TAX-050) and issue #22.

Issue #21: `Term.parent` must resolve through `ICV_TAXONOMY_TERM_MODEL`, not
TreeNode's `to="self"`, so that `makemigrations --check` reports no drift
when a consuming project swaps in its own AbstractTerm subclass. Before the
fix, AbstractTerm inherited `parent` unmodified from icv_tree.models.TreeNode.
`to="self"` resolved directly to the swapped subclass rather than through the
swappable setting, so its deconstruct() output permanently disagreed with the
package's frozen migration state (which targets
settings.ICV_TAXONOMY_TERM_MODEL), producing a spurious AlterField on
`parent` purely from exercising the swap seam.

Issue #22: icv_taxonomy's migrations FK to the swappable Term/Vocabulary
models via `getattr(settings, "ICV_TAXONOMY_*_MODEL", ...)` but declared no
`migrations.swappable_dependency(...)` edge, so nothing forced the swap
app's migrations to run before icv_taxonomy's. If the swap app's label sorts
AFTER "icv_taxonomy" (as "zappswap" deliberately does), `migrate` crashed
with `ValueError: Related model 'zappswap.appswapterm' cannot be resolved`.
The package's own fixture used to be named "appswap", which sorts BEFORE
"icv_taxonomy" and so took the working path by accident of alphabetical
ordering, masking the bug. Renaming it to "zappswap" makes this module a
real regression guard rather than an accidental pass.

Both tests run Django management commands in a subprocess against
tests/settings_migrate_swapped.py, which declares ICV_TAXONOMY_TERM_MODEL /
ICV_TAXONOMY_VOCABULARY_MODEL pointed at tests/zappswap's own subclasses and
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


def _run_django_command_script(script: str) -> subprocess.CompletedProcess[str]:
    """Run an inline Python script against the migrate-swapped settings.

    Same environment as _run_django_command, but for probes that need to
    inspect state after a management command rather than only its exit code.
    """
    env = dict(os.environ)
    env["DJANGO_SETTINGS_MODULE"] = "settings_migrate_swapped"
    env["PYTHONPATH"] = os.pathsep.join([str(SRC_DIR), str(TESTS_DIR)])

    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def test_migrate_succeeds_with_term_model_swapped() -> None:
    """`migrate` must apply cleanly when ICV_TAXONOMY_TERM_MODEL points at a
    consuming project's own AbstractTerm subclass.

    Also the regression test for issue #22: "zappswap" sorts AFTER
    "icv_taxonomy" alphabetically, so this only passes if icv_taxonomy's
    migrations carry a swappable_dependency edge forcing zappswap's
    migrations to run first. Without that edge, this fails with
    `ValueError: Related model 'zappswap.appswapterm' cannot be resolved`.
    """
    result = _run_django_command("migrate", "--noinput")

    assert result.returncode == 0, (
        f"migrate failed with ICV_TAXONOMY_TERM_MODEL swapped:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "cannot be resolved" not in result.stderr, (
        f"migrate hit the issue #22 unresolved-related-model crash:\nstderr:\n{result.stderr}"
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


def test_no_orphan_package_tables_when_models_are_swapped() -> None:
    """Guard D-G2 (ADR-074): under a swap, the package's own concrete tables
    must be ABSENT from the migrated schema.

    icv_taxonomy declares `swappable` in `0001_initial` itself rather than
    adding it to pre-existing history, so the strong form of D-G2 applies:
    there is no migration in which the tables are created before the option
    exists, and a correct `migrate` under a swap therefore creates neither
    `icv_taxonomy_term` nor `icv_taxonomy_vocabulary`.

    This is the property that failed for the consumer in #41. They vendored
    these migrations through `MIGRATION_MODULES` and their copy lost the
    `"swappable"` entry from the `CreateModel` options, so Django never
    learned the models were swapped out and created both tables on every
    database, including fresh ones. The tables then drifted from migration
    state and a later release's `AlterField` failed against them.

    `makemigrations --check` cannot catch this (`swappable` is not a key the
    autodetector compares), and neither can an in-process assertion on
    `Meta.swappable`, which reads the live model rather than migration state.
    Only the migrated schema shows it, which is why this runs `migrate` for
    real and then inspects the tables it produced.
    """
    script = (
        "import django; django.setup();"
        "from django.core.management import call_command;"
        "call_command('migrate', '--noinput', verbosity=0);"
        "from django.db import connection;"
        "t = set(connection.introspection.table_names());"
        "print('ORPHANS:' + ','.join(sorted("
        "t & {'icv_taxonomy_term', 'icv_taxonomy_vocabulary'})));"
        "print('SWAPTABLE:' + str('zappswap_appswapterm' in t))"
    )
    result = _run_django_command_script(script)

    assert result.returncode == 0, f"probe failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    # The swapped-in table must exist, otherwise the orphan assertion below
    # would pass vacuously on a migrate that created nothing at all.
    assert "SWAPTABLE:True" in result.stdout, (
        f"the swapped-in table was not created, so this test proves nothing:\nstdout:\n{result.stdout}"
    )

    orphans = next(line for line in result.stdout.splitlines() if line.startswith("ORPHANS:"))[len("ORPHANS:") :]

    assert orphans == "", (
        f"migrate created orphan package tables under a swap: {orphans}. "
        'The "swappable" option is missing from the CreateModel operations in '
        "migration state, so Django does not know these models are swapped out."
    )
