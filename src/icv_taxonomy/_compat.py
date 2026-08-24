"""Bundled default model base for icv-taxonomy (ADR-052).

``BaseModel`` here is the standalone default that actually runs when a
consumer sets neither ``ICV_TAXONOMY_BASE_MODEL`` nor ``ICV_BASE_MODEL``.
It references django-icv-core in no way at all: resolving a different base
is the consumer's choice, expressed through a settings string and handled
by :func:`icv_taxonomy.conf.get_base_model`.

Byte-compatibility is the invariant this module exists to hold. Every field
kwarg below matches ``icv_core.models.BaseModel`` exactly, so a consumer
that points ``ICV_BASE_MODEL`` at icv-core's base gets a model state
identical to the default one, and ``makemigrations`` detects no change in
either direction.

Do not "tidy" these kwargs. ``db_index=True`` on ``created_at`` and
``verbose_name`` on all three fields are load-bearing: ``help_text``,
``db_index`` and ``verbose_name`` are all part of ``Field.deconstruct()``,
so dropping one would put this base BELOW the package's own frozen
migrations and make the autodetector emit a compensating ``AlterField``
that drops a live index.
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class BaseModel(models.Model):
    """Standalone base: UUID primary key plus auto-managed timestamps.

    Field-for-field byte-compatible with ``icv_core.models.BaseModel``.
    Declares no ``Meta.ordering`` (ADR-066): an ordering on a shared base
    defeats ``values()``/``values_list()`` combined with ``distinct()`` in
    every inheriting model.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("created at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        abstract = True


__all__ = ["BaseModel"]
