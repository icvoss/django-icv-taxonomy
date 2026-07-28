"""Minimal test models for icv-taxonomy package tests."""

from __future__ import annotations

from django.db import models

from icv_taxonomy.models import AbstractVocabulary


class Scope(models.Model):
    """Stand-in for a consumer's tenant/site, to test AbstractVocabulary.scope_field."""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "taxonomy_testapp"

    def __str__(self) -> str:
        return self.name


class ScopedVocabulary(AbstractVocabulary):
    """A vocabulary whose name/slug uniqueness is scoped by a FK (scope_field).

    Regression fixture for icvoss/django-icv-taxonomy#3: two scopes may each
    have a "Sale" vocabulary. The package scopes by the field NAME only; the
    FK and its meaning are entirely consumer-side (here a plain Scope, in a
    real consumer a tenant).
    """

    scope_field = "scope"

    scope = models.ForeignKey(Scope, on_delete=models.CASCADE, related_name="vocabularies")

    class Meta(AbstractVocabulary.Meta):
        abstract = False
        app_label = "taxonomy_testapp"
        db_table = "taxonomy_testapp_scopedvocabulary"


class Article(models.Model):
    """Minimal model for testing term associations with a generic content object."""

    title = models.CharField(max_length=255)

    class Meta:
        app_label = "taxonomy_testapp"

    def __str__(self) -> str:
        return self.title


class Product(models.Model):
    """Second model for testing multi-type term associations."""

    name = models.CharField(max_length=255)

    class Meta:
        app_label = "taxonomy_testapp"

    def __str__(self) -> str:
        return self.name
