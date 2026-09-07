"""
Guard D-G3 (ADR-074): the ``swappable`` option must be present in MIGRATION
STATE, not merely in the model file's ``Meta``.

Why this guard exists rather than relying on the model file or on
``makemigrations --check``:

``swappable`` is not a key ``generate_altered_options`` compares, so
``--check`` is blind to its absence. A model file carrying
``Meta.swappable`` with no corresponding option in migration state passes
``--check``, passes the rest of this suite, and even makes the in-process
swap appear to work, because the model getter reads ``Meta.swappable`` off
the real model in memory. It fails only on a consumer's fresh ``migrate``,
where Django never learns the model was swapped out and so creates and keeps
managing an orphan ``icv_taxonomy_term`` / ``icv_taxonomy_vocabulary`` table
alongside the consumer's real one. Those orphans then drift from migration
state, and a later release that alters the model fails against them.

This is the failure a consumer hit in icvoss/django-icv-taxonomy#41 by
vendoring these migrations through ``MIGRATION_MODULES`` and losing the
option in the copy. The package's own migrations are correct; this guard is
what keeps them that way.

The state is built from the migration files ALONE. Never
``ProjectState.from_apps()``, which reads the app registry and so passes
even when the option is absent from every migration.

The state is built in a SUBPROCESS against ``settings_migrate_defaults``,
never in-process against the main suite's ``settings`` module. The main
suite sets ``MIGRATION_MODULES["icv_taxonomy"] = None`` so migrations never
run there, and ``tests/conftest.py``'s ``pytest_configure`` hook forces that
same override onto ANY settings module reached through pytest (it
unconditionally calls ``MIGRATION_MODULES.setdefault("icv_taxonomy", None)``
regardless of ``DJANGO_SETTINGS_MODULE``), which would make
``MigrationLoader`` unable to find these migration files at all if run
in-process. ``test_migrations_defaults.py`` hits the same problem and
resolves it the same way; this guard mirrors that pattern.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
SRC_DIR = TESTS_DIR.parent / "src"

# The swappable concrete models this package ships, and the setting each
# must name in migration state. Kept as literals rather than read from the
# models: a guard that sources its expectation from the thing under test
# cannot fail.
SWAPPABLE_MODELS = [
    ("term", "ICV_TAXONOMY_TERM_MODEL"),
    ("vocabulary", "ICV_TAXONOMY_VOCABULARY_MODEL"),
]

# Executed in a subprocess against settings_migrate_defaults: builds project
# state from the migration files on disk (never ProjectState.from_apps(),
# which reads the app registry) and prints the "swappable" option recorded
# against each icv_taxonomy model as JSON.
_PRINT_SWAPPABLE_OPTIONS = """
import json
import django

django.setup()
from django.db.migrations.loader import MigrationLoader

state = MigrationLoader(None, ignore_no_migrations=True).project_state()
result = {
    model_name: state.models[("icv_taxonomy", model_name)].options.get("swappable")
    for model_name in ("term", "vocabulary")
}
print(json.dumps(result))
"""


@pytest.fixture(scope="module")
def migration_swappable_options() -> dict[str, str | None]:
    """The ``swappable`` option recorded in migration state for each model.

    Built from the migration files on disk, in a subprocess configured with
    ``settings_migrate_defaults`` (real migrations enabled for icv_taxonomy),
    isolated from the parent pytest process's already-configured ``settings``
    module and its conftest override.
    """
    env = dict(os.environ)
    env["DJANGO_SETTINGS_MODULE"] = "settings_migrate_defaults"
    env["PYTHONPATH"] = os.pathsep.join([str(SRC_DIR), str(TESTS_DIR)])

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _PRINT_SWAPPABLE_OPTIONS],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, (
        f"failed to build migration state in subprocess:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    return json.loads(result.stdout)


@pytest.mark.parametrize(("model_name", "setting"), SWAPPABLE_MODELS)
def test_swappable_option_present_in_migration_state(migration_swappable_options, model_name, setting):
    """The migrations must declare the model swappable against its setting."""
    assert migration_swappable_options[model_name] == setting, (
        f"icv_taxonomy.{model_name} is missing the "
        f'"swappable": "{setting}" option in migration state. Without it, '
        "Django never learns the model can be swapped out and creates an "
        f"orphan icv_taxonomy_{model_name} table on every consumer database, "
        "including databases where the model IS swapped."
    )


def test_guard_reads_migrations_not_the_app_registry(migration_swappable_options):
    """Falsifiability control for the guard itself.

    The assertion above is only meaningful if the state it reads comes from
    the migration files. If a future refactor pointed the fixture at the app
    registry, the guard would pass on migrations that had lost the option
    entirely. Stripping the option from a COPY of the loaded state must make
    the same assertion fail, which proves the assertion is reading state
    that carries the option rather than a live model's Meta.
    """
    stripped = dict(migration_swappable_options)
    stripped["term"] = None

    assert stripped["term"] != "ICV_TAXONOMY_TERM_MODEL"
