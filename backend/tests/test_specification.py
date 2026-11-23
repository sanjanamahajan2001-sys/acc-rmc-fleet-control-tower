"""
Unit tests for Specification Pattern
"""

from app.models.base import BaseEntity
from app.repositories.specification import Specification


class DummyEntity(BaseEntity):
    __tablename__ = "dummy_entities"
    name: str = "test"


class NameEqualsSpec(Specification[DummyEntity]):
    def __init__(self, name: str):
        self.name = name

    def to_expression():
        pass


def test_specification_composition():
    # Verify logical operators instantiate correctly
    spec1 = NameEqualsSpec("A")
    spec2 = NameEqualsSpec("B")

    and_spec = spec1 & spec2
    or_spec = spec1 | spec2
    not_spec = ~spec1

    assert and_spec.left == spec1
    assert and_spec.right == spec2
    assert or_spec.left == spec1
    assert not_spec.spec == spec1
