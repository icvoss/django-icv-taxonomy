# Releasing

How to cut a release of django-icv-taxonomy. The package is versioned and
published independently to PyPI.

## TL;DR

```
branch  ->  PR  ->  review  ->  merge to main  ->  tag the merged commit  ->  CI publishes
```

The **tag is the trigger**. Pushing a tag of the form `v<semver>` (e.g.
`v0.5.0`) runs the publish workflow, which tests, builds, uploads to PyPI via
OIDC trusted publishing (no token required), and creates a GitHub release.
**Tagging is publishing. There is no separate "publish" step and no undo.**

## Canonical flow

1. **Branch** off `main`:
   `release/<version>` (e.g. `release/0.5.0`).
2. **Bump** on the branch:
   - `pyproject.toml` -> `version`
   - `src/icv_taxonomy/__init__.py` -> `__version__` (keep in sync)
   - `CHANGELOG.md` -> rename `[Unreleased]` to `[<version>] - <YYYY-MM-DD>` (today's date)
3. **Open a PR** to `main`. CI runs lint and tests. Get it reviewed. This is the
   gate: do not skip it.
4. **Merge to `main`** (squash or merge, per repo norm).
5. **Tag the merged commit on `main`** and push the tag:
   ```bash
   git checkout main && git pull
   git tag v<version>
   git push origin v<version>
   ```
6. **Watch the publish run** and confirm PyPI:
   ```bash
   gh run watch <run-id> --exit-status
   curl -s https://pypi.org/pypi/django-icv-taxonomy/json | python -c \
     "import sys,json;print(json.load(sys.stdin)['info']['version'])"
   ```

> **Tag the commit that is on `main`, not a feature branch.** Tags point at
> commits, not branches, so tagging a feature branch will publish, but it
> publishes code that may never have been merged. Always tag after the merge so
> what is on PyPI is exactly what is on `main`.

## Tag format (strict)

`v<semver>`: the literal `v` prefix, then the version. No package prefix.

Examples: `v0.4.0`, `v0.5.0`, `v1.0.0`.

## Dependency on django-icv-tree

django-icv-taxonomy depends on `django-icv-tree>=0.2.0` (from PyPI). If your
release requires changes that are only available in an unreleased version of
django-icv-tree, you must:

1. Release the required django-icv-tree version first (from its own repo).
2. Bump the `django-icv-tree` dependency floor in `pyproject.toml` to match.
3. Include that floor bump in the same PR as the taxonomy change.

Do not tag a taxonomy release that requires an unpublished django-icv-tree
version: CI will install from PyPI and the tests will run against the wrong
version.

## Version locations

The version string lives in two places and must be kept in sync:

- `pyproject.toml`: `version = "0.4.0"`
- `src/icv_taxonomy/__init__.py`: `__version__ = "0.4.0"`

Both are updated on the release branch before the PR is opened.

## Versioning (SemVer)

[Semantic Versioning](https://semver.org/). Pre-1.0, the rules still apply with
the usual pre-1.0 caveat that minor bumps may carry breaking changes:

- **Patch** (`0.4.0 -> 0.4.1`): bug fixes, doc-only changes, no API or
  behaviour change.
- **Minor** (`0.4.0 -> 0.5.0`): new public API, any behaviour change (even a
  safer one), or a raised minimum dependency floor (e.g. Django or icv-tree).
- **Major** (`0.x -> 1.0`): the stability commitment; breaking changes after 1.0.

If in doubt between patch and minor, choose minor. Burning a version number is
free; shipping a behaviour change as a patch surprises consumers.

## CHANGELOG (required for every release)

**A release must include a CHANGELOG entry for its version. No entry, no tag.**
CI enforces this: the publish workflow will fail if `CHANGELOG.md` does not
contain a heading matching `## [<version>]`.

[Keep a Changelog](https://keepachangelog.com/) format. Accumulate entries under
`## [Unreleased]` as you work; at release time, rename that heading to
`## [<version>] - <YYYY-MM-DD>`. Subsections: Added / Changed / Fixed / Removed.
Call out behaviour changes explicitly, including ones that are "safer".

The GitHub release body is auto-generated from the tag, but that is not a
substitute for the curated CHANGELOG entry. Write the CHANGELOG by hand so
consumers reading the package on PyPI get a human-authored summary.

## Pre-tag checklist

Before pushing the tag (the irreversible step):

- [ ] **CHANGELOG has a `[<version>] - <date>` entry** (renamed from `[Unreleased]`).
- [ ] Behaviour changes and breaking changes called out in that CHANGELOG entry.
- [ ] Version bumped in `pyproject.toml` and `src/icv_taxonomy/__init__.py`, and they match.
- [ ] CI Django pin matches the package's minimum floor, if the floor changed.
- [ ] Tests pass locally and the package builds (`python -m build` at repo root).
- [ ] The PR is **merged to `main`** and you are tagging that commit.
- [ ] Tag format is `v<version>` (e.g. `v0.5.0`).
- [ ] This exact version has never been published (PyPI rejects re-uploads).

## If something goes wrong

- **PyPI rejects the upload (version exists).** That version is permanently
  taken; you cannot re-upload, even after deleting. Bump to the next patch and
  re-tag.
- **The test/build job fails after tagging.** Nothing was published (publish is
  the last job and depends on test + build). Fix on a new PR, merge, delete the
  bad tag (`git push --delete origin <tag>`), and re-tag the new commit with the
  same version (since nothing reached PyPI).
- **Published, but the code is not on `main`.** Open a PR from the release
  branch to `main` immediately and merge, so `main` reflects what is on PyPI.
  Avoid this by always tagging after the merge.

## Optional hardening

Consider adding a manual approval gate to the `publish` job via a protected
GitHub Environment (`pypi`), so "push tag" and "irreversibly upload to PyPI"
are decoupled: a human approves the upload after seeing test and build go green.
The publish workflow already declares `environment: pypi`; add a
required-reviewer protection rule to that environment to enable the gate.
