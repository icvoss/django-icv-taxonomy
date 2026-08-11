# Changelog

All notable changes to django-icv-taxonomy are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed

- **`get_terms_for_object()` and `get_terms_for_object_typed()` docstrings
  no longer promise association order** (#25). The functions have always
  returned terms in the Term model's default tree path order: the
  association queryset's ordering is discarded by the `pk__in` subquery, so
  the documented "ordered by association order and creation time" was never
  delivered. The docstrings now state the real contract, and the dead
  `order_by("order", "created_at")` on the subquery has been removed
  (behaviour unchanged). Association-order retrieval can be added later as
  an explicit opt-in if a consumer needs it.
- **Migrations that FK to the swappable `Term`/`Vocabulary` models now carry
  a `swappable_dependency` edge** (#22). The migrations resolved the FK
  target via `getattr(settings, "ICV_TAXONOMY_*_MODEL", ...)` but declared
  no dependency forcing the swap app's migrations to run first, so Django
  fell back to default app-processing order. A consuming app whose label
  sorts after `icv_taxonomy` alphabetically (most consumer names, by chance)
  crashed on first `migrate` with `ValueError: Related model
  '<app>.<model>' cannot be resolved`, because icv_taxonomy's migrations ran
  before the app providing the swapped model. Renaming the same app to sort
  before `icv_taxonomy` made the crash disappear, with nothing else changed,
  which is how it went unnoticed: the package's own swap fixture
  (`tests/appswap`, now renamed `tests/zappswap`) happened to sort first.

  Both migration graphs that resolve the FK through settings now declare
  `migrations.swappable_dependency(...)` for both
  `ICV_TAXONOMY_VOCABULARY_MODEL` and `ICV_TAXONOMY_TERM_MODEL`: the
  squashed `0001_squashed_0003_alter_term_vocabulary_alter_termassociation_term_and_more`
  (fresh installs) and the original
  `0003_alter_term_vocabulary_alter_termassociation_term_and_more` (existing
  installs still on the pre-squash chain). This is the same pattern Django
  itself uses for `AUTH_USER_MODEL`, and it is a no-op when the model is not
  swapped, since Django's loader ignores a `__first__` self-reference to the
  same app. No `operations` changed in either migration file: this is purely
  a graph-ordering fix.

  Found while verifying the fix for #21.

- **`Term.parent` now resolves through `ICV_TAXONOMY_TERM_MODEL`, not
  TreeNode's `to="self"`** (#21). `AbstractTerm` inherited `parent` unmodified
  from `icv_tree.models.TreeNode`, whose `to="self"` resolves at
  class-definition time against whichever concrete class the field lands on.
  That is correct for a non-swappable `TreeNode` consumer, but `Term` is
  swappable. When a consuming project pointed `ICV_TAXONOMY_TERM_MODEL` at its
  own `AbstractTerm` subclass, `parent` still resolved to that subclass
  directly rather than through the swappable setting, so its `deconstruct()`
  output permanently disagreed with the package's frozen migration state
  (which targets `settings.ICV_TAXONOMY_TERM_MODEL`, the same as every other
  FK to `Term`). This produced a spurious `AlterField` on `parent` under
  `makemigrations --check`, purely from exercising the documented swap seam.

  `AbstractTerm` now redeclares `parent` explicitly using the same
  `getattr(django_settings, "ICV_TAXONOMY_TERM_MODEL", "icv_taxonomy.Term")`
  pattern already used by `TermRelationship.term_from`/`term_to` and
  `TermAssociation.term`, preserving every other kwarg (`null`, `blank`,
  `on_delete=CASCADE`, `related_name="children"`, `db_index=True`,
  `verbose_name`, `help_text`). No migration ships with this change: the
  package's frozen migration state already targeted the swappable setting for
  `parent`, so the model now simply agrees with it, under both the swapped
  and unswapped (default) configurations.

  Found while building the `tests/consumer` consumer smoke-test harness (#20,
  ADR-027), which now gates on exactly this class of defect.

- **`cleanup_orphaned_associations()` no longer under-counts orphans when an
  object carries more than one term.** Both `values_list(...).distinct()`
  calls in the cleanup loop relied on Django's automatic `DISTINCT` without
  first clearing queryset ordering. `TermAssociation`'s default ordering is
  `["order", "created_at"]` (BR-TAX-044), which Django appends to the
  `SELECT` unless explicitly cleared, so `DISTINCT` was applied to the
  `(object_id, order, created_at)` tuple rather than `object_id` alone. Since
  `order` increments per association on the same object (BR-TAX-019) and
  `created_at` is `auto_now_add`, an orphaned object with several
  associations returned the same `object_id` once per association instead of
  once per object, feeding a duplicated value into the follow-up
  `object_id__in=...` filter. The final counts happened to still be correct,
  because SQL `IN` deduplicates its list, but the intermediate work was
  needlessly repeated per association rather than per object. Both call
  sites now insert `.order_by()` before `.distinct()` to clear the inherited
  ordering first.

## [1.0.2] - 2026-08-10

### Fixed

- **No-op release. Its original entry was wrong and is corrected here.** 1.0.2
  was cut on the mistaken belief that the published 1.0.1 artefact lacked
  `0005_alter_term_path`. It does not: 1.0.1 shipped that migration correctly,
  as does its git tag. The consumer failure that prompted this release came from
  a stale pin (`django-icv-taxonomy==1.0.0`, predating the fix), not from a
  missing artefact. There is no code difference between 1.0.1 and 1.0.2, and
  nothing needs upgrading from 1.0.1. Left published rather than yanked.

## [1.0.1] - 2026-08-09

### Fixed

- **`Term.path` migration for django-icv-tree 1.0.0** (#12). Tree 1.0.0 removed
  an em dash from `TreeNode.path`'s `help_text`. `TreeNode` is abstract, so
  every consumer subclass freezes that exact string into its own migration via
  `Field.deconstruct()`, which made Django's autodetector demand a migration
  here. `0005_alter_term_path` supplies it.

  `help_text` only: `max_length`, `db_index`, `editable` and `verbose_name` are
  unchanged, so it is a no-op at the database level. It still mattered, because
  `makemigrations --check` is a deploy gate in consuming sites, so every
  consumer on tree 1.0.0 had a red CI and a blocked deploy until this shipped.

### Changed

- The `django-icv-tree` floor is raised to `>=1.0.0`. Migration 0005 freezes
  the `help_text` as that release words it, so resolving an older tree would
  report the inverse drift and fail a consumer's `makemigrations --check` in
  the opposite direction.

---

## [1.0.0] - 2026-08-09

### Fixed

- **`import_vocabulary()` no longer skips child terms on the first import of a
  hierarchical vocabulary** (issue #4). The classification loop resolved a
  new term's parent from a map that was only updated for **existing**
  terms; a newly-created parent was registered only in a later, separate
  create loop, after every child's skip decision had already been made. On
  a first import of a fully new tree, every non-root term was silently
  counted as `skipped`. Import now classifies and creates each term in a
  single pass, registering a new term against its slug immediately so
  later entries in the same pass can resolve it as a parent. A parent slug
  that is genuinely absent (not an existing term, not an earlier entry in
  the same import) is still skipped. If you were retrying `import_vocabulary()`
  in a loop until `created == 0` to work around this, that workaround is no
  longer necessary.

- **`tag_object()` is now concurrency-safe for single-value vocabularies**
  (issue #6). The `allow_multiple=False` cardinality check was a plain
  check-then-insert: two concurrent requests could each see zero existing
  associations and both create a term from the same single-value vocabulary
  for the same object. `vocabulary` lives on the `Term` table, not on
  `TermAssociation`, so the condition cannot be expressed as a database
  constraint on `TermAssociation` alone. `tag_object()` now takes
  `select_for_update()` on the vocabulary row inside an atomic transaction
  before re-checking cardinality for `allow_multiple=False` vocabularies,
  serialising concurrent single-value taggers on that vocabulary. The
  losing request raises `TaxonomyValidationError` (BR-TAX-016); a
  duplicate-tag race on the same term is caught by the existing unique
  constraint and mapped to the same exception type. Multi-value and
  generic-object tagging behaviour is unchanged.

---

## [0.6.0] - 2026-07-28

### Added

- **`AbstractVocabulary.scope_field`: per-scope name/slug uniqueness**
  (issue #3). A subclass that adds a scoping field (for example a `tenant` or
  `site` FK) can make vocabulary `name`/`slug` unique **within that scope**
  instead of globally, so two scopes may each have a "Sale" vocabulary, by
  setting `scope_field = "<field>"` (mirroring `AbstractTerm.tree_scope_field`):

  ```python
  class Vocabulary(AbstractVocabulary):
      tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
      scope_field = "tenant"
  ```

  The package is **tenancy-agnostic**: it scopes uniqueness by whatever field
  name is given and never reads a tenant model or `ICV_TENANT_MODEL`. The
  consumer owns the FK and its meaning. `scope_field = None` (the default)
  keeps global uniqueness.

### Changed

- `AbstractVocabulary.name` and `.slug` no longer carry field-level
  `unique=True`; uniqueness is now expressed as named `UniqueConstraint`s
  computed from `scope_field` (on the `class_prepared` signal, which fires
  after `_meta` is built). For the default `Vocabulary` this is a behavioural
  no-op (same global uniqueness, now as
  `icv_taxonomy_vocabulary_{name,slug}_uniq`). Migration
  `0004_vocabulary_scope_field_uniqueness` applies the swap on the default
  model; a consumer's swapped-in subclass carries its own scoped constraints
  in its own app's migrations.

## [0.5.1] - 2026-07-12

### Fixed

- Migrations resolve ICV_TAXONOMY_VOCABULARY_MODEL/ICV_TAXONOMY_TERM_MODEL via
  getattr with the package defaults, so a project that does not declare these
  settings no longer crashes on migrate/makemigrations.

## [0.5.0] - 2026-07-09

### Added

- Squashed migration `0001_squashed_0003_alter_term_vocabulary_alter_termassociation_term_and_more` replacing 0001 to 0003. Existing
  databases that applied the original series are unaffected (Django
  no-ops through the `replaces` list); fresh installs apply the single
  squashed migration. The replaced originals remain in the package and
  will be removed in the next major release once all installations have
  passed the squash point.

### Changed

- Minimum Django is now 5.2 (was 5.0). Django 5.2 and 6.0 are the
  supported and CI-tested versions.
- Packaging: the build backend now requires setuptools 77+ (PEP 639
  SPDX licence metadata) and no longer lists wheel; project URLs point
  at the icvoss GitHub organisation.

## [0.4.0] - 2026-06-24

### Added

- `icv_taxonomy.tasks.cleanup_orphaned_associations_task`: a schedulable
  Celery task wrapping `cleanup_orphaned_associations()`. `TermAssociation`
  uses a `GenericForeignKey` with no database cascade, so deleting a tagged
  object leaves orphan rows (BR-TAX-018); this gives projects an automatic,
  beat-schedulable cleanup instead of relying solely on a manual call. Celery
  is optional; without it the task is a plain callable. README documents the
  cleanup obligation and how to schedule it.

### Fixed

- Admin registration (`_register_admin`) no longer swallows failures silently.
  A misconfigured swappable model (`ICV_TAXONOMY_VOCABULARY_MODEL` /
  `ICV_TAXONOMY_TERM_MODEL`) previously produced a silently-missing admin via
  `except Exception: pass`. It now logs a `WARNING` (with traceback) so the
  misconfiguration is visible, while the benign `AlreadyRegistered` case stays
  quiet.

## [0.3.2] - 2026-04-20

### Fixed

- Standalone fallback base model now provides UUID primary key and
  `created_at`/`updated_at` timestamps (matching `icv_core.BaseModel`)
  instead of bare `models.Model`. Installing icv-taxonomy without
  django-icv-core no longer breaks the model schema.
- Admin no longer conditionally hides timestamp fields when icv-core is
  absent; timestamps are always present and always shown.

## [0.3.1] - 2026-04-18

### Fixed

- `AbstractTermRelationship` and `AbstractTermAssociation` now declare
  `id = models.BigAutoField(...)` explicitly instead of relying on
  `default_auto_field` resolution. Consumer projects with a different
  `DEFAULT_AUTO_FIELD` setting no longer get phantom `AlterField`
  migrations for these junction tables.

## [0.3.0] - 2026-04-08

Promoted to Production/Stable.

### Added

- `clear_vocabulary(vocab)`: delete all terms without deleting the
  vocabulary; single bulk DELETE with database CASCADE
- 50 new tests covering admin, management commands, template tags,
  clear_vocabulary, and signal emission

### Changed

- `merge_terms()` rewritten with bulk operations: batch duplicate
  detection, bulk UPDATE for associations/relationships, `bulk_update()`
  for child reparenting. ~1,800 queries → ~18 for a typical merge (100x).
- `import_vocabulary()` uses `bulk_update()` for existing terms instead
  of per-term `save()`. ~30,000 queries → ~100 for 10K terms (300x).
- VocabularyAdmin resolves term related_name dynamically via
  `_get_term_related_name()` instead of hardcoded `"term_set"`, fixing
  breakage with custom Term subclasses via `ICV_TAXONOMY_TERM_MODEL`.

### Fixed

- `__version__` synced with pyproject.toml (was 0.1.0, now 0.3.0)
- `%(class)s_set` related_name pattern on all ForeignKeys for swappable
  model support

## [0.2.1] - 2026-03-30

### Fixed

- Add missing `swappable` Meta attribute to concrete `Vocabulary` and `Term` models
- Add missing `swappable` option to `0001_initial` migration for both models

## [0.2.0] - 2026-03-30

### Changed

- Require Django >= 5.0; dropped Django 4.2 support
- Require Python >= 3.11
- Added Django 6.0 classifier

## [0.1.1] - 2026-03-29

### Changed

- Bumped minimum `django-icv-tree` dependency to >= 0.1.1
- Promoted Development Status to Beta

## [0.1.0] - 2026-03-27

### Added

- `AbstractVocabulary` and `AbstractTerm` abstract base models for subclassing
- Concrete `Vocabulary`, `Term`, `TermRelationship`, and `TermAssociation` models
- Swappable models via `ICV_TAXONOMY_VOCABULARY_MODEL` and `ICV_TAXONOMY_TERM_MODEL`
  settings (AUTH_USER_MODEL pattern)
- `get_vocabulary_model()` and `get_term_model()` runtime resolution functions
- `VocabularyManager` and `TaxonomyTermManager` with active-object filtering
- Service layer: vocabulary management, term management, tagging, relationships,
  import/export, and bulk operations
- `create_term_m2m()` factory for typed many-to-many relationships
- `AbstractTermAssociation` for generic tagging via Django's `GenericForeignKey`
- `AbstractTermRelationship` for SKOS-style semantic links between terms
- System checks `icv_taxonomy.E001` and `icv_taxonomy.E002` for swappable settings
  validation
- Signal handlers bridging `icv_tree.node_moved` to `taxonomy.term_moved`
- Admin integration with lazy registration for swappable models
