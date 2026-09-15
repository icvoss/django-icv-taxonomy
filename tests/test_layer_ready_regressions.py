"""Regression coverage for the taxonomy layer-ready acceptance cases."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError


@pytest.mark.django_db
class TestTermM2MFactory:
    def test_rejects_non_model_input(self):
        from icv_taxonomy.models import create_term_m2m

        with pytest.raises(TypeError, match="BR-TAX-044"):
            create_term_m2m(object())

    def test_returns_abstract_join_shape_for_lazy_model_reference(self):
        from icv_taxonomy.models import create_term_m2m

        join_model = create_term_m2m("taxonomy_testapp.Article")

        assert join_model._meta.abstract
        assert join_model._meta.get_field("term").remote_field.model == "icv_taxonomy.Term"
        assert join_model._meta.get_field("content_object").remote_field.model == "taxonomy_testapp.Article"
        assert join_model._meta.ordering == ["order", "created_at"]


@pytest.mark.django_db
class TestTypedM2MIsolation:
    def test_generic_and_typed_tagging_use_separate_join_tables(self, article):
        from django.apps import apps
        from taxonomy_testapp.models import ArticleTerm

        from icv_taxonomy.services import create_term, create_vocabulary, tag_object

        vocabulary = create_vocabulary(name="Topics")
        term = create_term(vocabulary=vocabulary, name="Django")
        tag_object(term, article)

        TermAssociation = apps.get_model("icv_taxonomy", "TermAssociation")
        assert TermAssociation.objects.filter(term=term).count() == 1
        assert ArticleTerm.objects.count() == 0

        ArticleTerm.objects.create(term=term, content_object=article)
        assert TermAssociation.objects.filter(term=term).count() == 1
        assert ArticleTerm.objects.filter(term=term, content_object=article).count() == 1


@pytest.mark.django_db
class TestRelationshipProofs:
    def test_cross_vocabulary_relationship_is_preserved(self):
        from icv_taxonomy.services import add_relationship, create_term, create_vocabulary, get_related_terms

        first = create_vocabulary(name="First")
        second = create_vocabulary(name="Second")
        source = create_term(vocabulary=first, name="Source")
        target = create_term(vocabulary=second, name="Target")

        add_relationship(source, target, "see_also")

        assert list(get_related_terms(source)) == [target]

    def test_invalid_relationship_type_is_refused_before_writing(self):
        from django.apps import apps

        from icv_taxonomy.exceptions import TaxonomyValidationError
        from icv_taxonomy.services import add_relationship, create_term, create_vocabulary

        vocabulary = create_vocabulary(name="Topics")
        source = create_term(vocabulary=vocabulary, name="Source")
        target = create_term(vocabulary=vocabulary, name="Target")

        with pytest.raises(TaxonomyValidationError, match="Unknown relationship type"):
            add_relationship(source, target, "invalid")

        TermRelationship = apps.get_model("icv_taxonomy", "TermRelationship")
        assert not TermRelationship.objects.exists()

    def test_merge_transfers_relationships_and_discards_self_loops(self):
        from django.apps import apps

        from icv_taxonomy.services import add_relationship, create_term, create_vocabulary, merge_terms

        vocabulary = create_vocabulary(name="Topics")
        source = create_term(vocabulary=vocabulary, name="Source")
        target = create_term(vocabulary=vocabulary, name="Target")
        other = create_term(vocabulary=vocabulary, name="Other")
        add_relationship(source, other, "see_also")
        add_relationship(source, target, "see_also")

        result = merge_terms(source, target)

        TermRelationship = apps.get_model("icv_taxonomy", "TermRelationship")
        assert result["relationships_transferred"] == 1
        assert TermRelationship.objects.filter(term_from=target, term_to=other, relationship_type="see_also").exists()
        assert not TermRelationship.objects.filter(term_from=target, term_to=target).exists()

    def test_merge_rolls_back_transfers_when_source_deactivation_fails(self, monkeypatch, article):
        from django.apps import apps

        from icv_taxonomy.services import create_term, create_vocabulary, merge_terms, tag_object

        vocabulary = create_vocabulary(name="Topics")
        source = create_term(vocabulary=vocabulary, name="Source")
        target = create_term(vocabulary=vocabulary, name="Target")
        tag_object(source, article)

        def fail_save(*args, **kwargs):
            raise RuntimeError("deactivation failed")

        monkeypatch.setattr(source, "save", fail_save)

        with pytest.raises(RuntimeError, match="deactivation failed"):
            merge_terms(source, target)

        TermAssociation = apps.get_model("icv_taxonomy", "TermAssociation")
        assert TermAssociation.objects.filter(term=source).count() == 1
        assert not TermAssociation.objects.filter(term=target).exists()


@pytest.mark.django_db
class TestEmptyVocabularyEdges:
    def test_empty_vocabulary_exports_imports_and_deletes(self):
        from icv_taxonomy.models import Vocabulary
        from icv_taxonomy.services import delete_vocabulary, export_vocabulary, import_vocabulary

        vocabulary = Vocabulary.objects.create(name="Empty", slug="empty")
        exported = export_vocabulary(vocabulary)
        assert exported["terms"] == []
        assert exported["relationships"] == []

        result = import_vocabulary(exported)
        assert result == {"created": 0, "updated": 0, "skipped": 0, "relationships_skipped": 0}

        delete_vocabulary(vocabulary)
        assert not Vocabulary.all_objects.filter(pk=vocabulary.pk).exists()


@pytest.mark.django_db
class TestVisibleValidationFailures:
    def test_dangling_parent_is_not_treated_as_root(self):
        from icv_taxonomy.models import Term
        from icv_taxonomy.services import create_vocabulary

        vocabulary = create_vocabulary(name="Shallow", vocabulary_type="hierarchical", max_depth=1)
        term = Term(vocabulary=vocabulary, name="Orphan", slug="orphan")
        term.parent_id = "00000000-0000-0000-0000-000000000001"

        with pytest.raises(ValidationError, match="Parent term does not exist"):
            term.full_clean()


@pytest.mark.django_db
class TestImportRelationshipOutcome:
    def test_reports_unresolvable_relationships(self):
        from icv_taxonomy.services import import_vocabulary

        result = import_vocabulary(
            {
                "name": "Imported",
                "slug": "imported",
                "terms": [],
                "relationships": [
                    {
                        "term_from_slug": "missing",
                        "term_to_slug": "also-missing",
                        "relationship_type": "related",
                    }
                ],
            }
        )

        assert result["relationships_skipped"] == 1
