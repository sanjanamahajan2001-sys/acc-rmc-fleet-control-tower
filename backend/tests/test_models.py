"""
Unit tests for Declarative Base Model Hierarchy
"""

from app.models.base import NAMING_CONVENTION, VersionedEntity


class ConcreteTestModel(VersionedEntity):
    __tablename__ = "test_concrete_entities"


def test_naming_convention_dictionary():
    assert NAMING_CONVENTION["pk"] == "pk_%(table_name)s"
    assert (
        NAMING_CONVENTION["fk"]
        == "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
    )


def test_model_columns_and_defaults():
    instance = ConcreteTestModel()
    assert instance.is_deleted in (False, None)
    assert instance.version_id in (1, None)
    assert instance.deleted_at is None
