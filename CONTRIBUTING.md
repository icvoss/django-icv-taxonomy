# Contributing to django-icv-taxonomy

Practical guide for contributors working on this package.

---

## Prerequisites

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Django 5.1 or later (installed as part of the dev setup)
- No database server required: the test suite uses SQLite.

---

## Local Development Setup

```bash
git clone https://github.com/icvoss/django-icv-taxonomy.git
cd django-icv-taxonomy

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install in editable mode with test dependencies
pip install -e .
pip install "Django~=5.1" pytest pytest-django pytest-cov pytest-mock factory-boy ruff
```

django-icv-tree (the tree library this package depends on) is installed from
PyPI as part of `pip install -e .`. You do not need to check it out locally
unless you are working on it at the same time. If you are, install it in
editable mode from its repo first:

```bash
pip install -e /path/to/django-icv-tree
pip install -e .
```

---

## Running Tests

Tests use SQLite and require no database server.

```bash
DJANGO_SETTINGS_MODULE=settings PYTHONPATH=src:tests pytest tests/ -v --tb=short
```

Or, with pytest configured in `pyproject.toml`, simply:

```bash
pytest tests/ -v --tb=short
```

---

## Code Standards

All Python code is linted and formatted with [ruff](https://docs.astral.sh/ruff/),
configured in `pyproject.toml`.

| Setting | Value |
|---------|-------|
| Line length | 120 |
| Quote style | Double |
| Target Python | 3.11 |

```bash
ruff check .            # lint
ruff format --check .   # format check (no writes)
ruff format .           # format in place
```

CI will fail if either check reports errors. Run both checks before pushing.

---

## Repository Structure

```
django-icv-taxonomy/
    src/icv_taxonomy/      # importable package
    tests/
        settings.py        # Django settings for the test suite
        conftest.py        # shared fixtures
    pyproject.toml         # package metadata, dependencies, tool config
    CHANGELOG.md
    README.md
    RELEASING.md
```

The package uses the src layout: `src/icv_taxonomy` is the importable module.
Tests live alongside the source in `tests/` at the repo root.

---

## Git Workflow

### Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

| Type | When to use |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `chore` | Maintenance, version bumps, dependency updates |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `style` | Formatting, whitespace; no logic change |
| `refactor` | Code change that is neither a fix nor a feature |

Scope is optional; use `taxonomy` if in doubt.

### Branches and PRs

Push feature branches and open a pull request against `main`. CI must pass
before merging. Prefer small, focused commits over large ones.

---

## Releasing

See [RELEASING.md](RELEASING.md) for the full release process. In brief:

1. Bump the version in `pyproject.toml` and `src/icv_taxonomy/__init__.py`.
2. Update `CHANGELOG.md`: rename `[Unreleased]` to `[<version>] - <date>`.
3. Open a PR, get it reviewed, merge.
4. Tag the merged commit on `main`: `git tag v<version> && git push origin v<version>`.

CI handles the rest: tests, build, PyPI upload, GitHub release.
