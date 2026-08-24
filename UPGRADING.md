# Upgrading django-icv-taxonomy

Cumulative upgrade notes, written for the version you are moving **from**
rather than the version you are moving **to**.

The CHANGELOG records what changed in each release. This file records what
you have to *do*, and it is deliberately cumulative: a consumer jumping
several versions at once crosses intermediate entries without ever reading
them, which is exactly where an upgrade note gets missed.

If a version range is not listed here, the upgrade needs nothing beyond
`pip install -U` and `migrate`.

---

## 0.5.x to 1.0.x

**Required action: none.** Run `migrate` as usual.

Two migrations apply that are worth understanding before a production
deploy, because one of them looks alarming in a `sqlmigrate` diff and is
not.

### `0004_vocabulary_scope_field_uniqueness` (from 0.6.0)

This migration **changes how `Vocabulary.name` and `.slug` uniqueness is
enforced. It does not change what is unique.**

Before, on 0.5.x, both fields carried field-level `unique=True`. After, the
same single-column uniqueness is enforced by named constraints,
`icv_taxonomy_vocabulary_name_uniq` and `icv_taxonomy_vocabulary_slug_uniq`.
Same two columns, same global uniqueness, different mechanism.

**No data condition can make this migration fail.** Duplicate vocabulary
names and slugs were not representable on 0.5.x, because the unique index
being replaced already forbade them. If your database ran 0.5.x
successfully, it cannot be holding a row that the new constraints reject.
You do not need a pre-flight duplicate check, and you do not need a
maintenance window for data remediation.

The reason for the change is `AbstractVocabulary.scope_field`. A named
constraint can be recomputed by a subclass; a field-level `unique=True`
cannot. Setting `scope_field` lets a subclass make name and slug unique
*within a scope* (a tenant, a site) instead of globally:

```python
class Vocabulary(AbstractVocabulary):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    scope_field = "tenant"
```

`scope_field = None` is the default and keeps global uniqueness, so the
default `Vocabulary` model is unaffected in behaviour.

**Operational note.** On PostgreSQL this migration emits:

```sql
DROP INDEX IF EXISTS "icv_taxonomy_vocabulary_name_761e9e7b_like";
CREATE INDEX "icv_taxonomy_vocabulary_slug_eca05ef8" ON "icv_taxonomy_vocabulary" ("slug");
ALTER TABLE "icv_taxonomy_vocabulary" ADD CONSTRAINT "icv_taxonomy_vocabulary_name_uniq" UNIQUE ("name");
ALTER TABLE "icv_taxonomy_vocabulary" ADD CONSTRAINT "icv_taxonomy_vocabulary_slug_uniq" UNIQUE ("slug");
```

Each `ADD CONSTRAINT ... UNIQUE` builds a new unique index and holds an
`ACCESS EXCLUSIVE` lock on `icv_taxonomy_vocabulary` while it does. That is
the ordinary lock any non-`CONCURRENTLY` `ALTER TABLE` takes. Uniqueness is
enforced continuously across the whole migration: the replacement index is
built before the implicit one it supersedes is gone, so there is no window
in which a duplicate could be inserted.

A vocabulary table holds tens to hundreds of rows in any realistic
deployment, so this is a matter of milliseconds. It is only worth planning
around if you have an unusually large `Vocabulary` table, in which case
treat it as you would any other index build on that table. Note also that
the plain (non-unique) `slug` index is new: dropping `unique=True` from a
`SlugField` leaves its `db_index` behind.

### `0005_alter_term_path` (from 1.0.1)

A cosmetic `AlterField` on `Term.path`, no data change, picking up a
`help_text` string that django-icv-tree 1.0.0 reworded.

**Upgrade to at least 1.0.1 if you use django-icv-tree 1.0.0 or later.**
`Term` subclasses tree's abstract `TreeNode`, and `help_text` is part of
`Field.deconstruct()`, so the reworded string has to be frozen into this
package's own migrations. On taxonomy 1.0.0 with tree 1.0.0 installed, an
unscoped `manage.py makemigrations --check --dry-run` reports an unmigrated
`Term.path` and fails. Since 1.0.1 the package declares
`django-icv-tree>=1.0.0` for the same reason: an older tree would put the
previous wording back on the abstract base and produce the inverse drift.

If you narrowed your own `makemigrations --check` to first-party apps to
work around this, you can restore the unscoped check once you are on 1.0.1
or later.

### Behaviour changes in this range

- **1.0.0** fixed `import_vocabulary()` silently skipping child terms on the
  first import of a hierarchical vocabulary. If you were retrying the import
  in a loop until `created == 0` as a workaround, that is no longer needed.
- **1.0.0** made `tag_object()` concurrency-safe for single-value
  vocabularies. The losing request in a race now raises
  `TaxonomyValidationError` (BR-TAX-016) rather than creating a second
  association.
- **1.0.3** removed the default `Meta.ordering` from the bundled fallback
  base model (ADR-066), because a `Meta.ordering` on a shared base defeats
  `values()`/`values_list()` combined with `distinct()` in every inheriting
  model. `AbstractVocabulary` (`ordering = ["name"]`) and `AbstractTerm`
  (`ordering = ["path"]`) declare their own ordering, so neither changes. It
  affects you only if you have your own model inheriting the fallback base
  and relying on it sorting by `-created_at` implicitly; add an explicit
  `ordering` to that model if so.
- **1.0.3** also fixed two swap-seam defects that only affect consumers
  using `ICV_TAXONOMY_TERM_MODEL` or `ICV_TAXONOMY_VOCABULARY_MODEL`. If a
  first `migrate` previously failed with `ValueError: Related model ...
  cannot be resolved`, or `makemigrations --check` reported a spurious
  `AlterField` on `Term.parent`, both are resolved.
