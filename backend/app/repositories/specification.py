"""
Specification Pattern Implementation

Provides abstract Specification[T] and logical expression operators (And, Or, Not)
to build dynamic, composable SQLAlchemy queries without proliferation of repository methods.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy.sql.elements import ColumnElement

T = TypeVar("T")


class Specification(ABC, Generic[T]):
    """
    Abstract Specification base class returning SQLAlchemy ColumnElement expressions.
    """

    @abstractmethod
    def to_expression(self) -> ColumnElement[bool]:
        """Returns the underlying SQLAlchemy binary expression."""

    def __and__(self, other: "Specification[T]") -> "Specification[T]":
        return AndSpecification(self, other)

    def __or__(self, other: "Specification[T]") -> "Specification[T]":
        return OrSpecification(self, other)

    def __invert__(self) -> "Specification[T]":
        return NotSpecification(self)


class AndSpecification(Specification[T]):
    """Logical AND of two specifications."""

    def __init__(self, left: Specification[T], right: Specification[T]):
        self.left = left
        self.right = right

    def to_expression(self) -> ColumnElement[bool]:
        return self.left.to_expression() & self.right.to_expression()


class OrSpecification(Specification[T]):
    """Logical OR of two specifications."""

    def __init__(self, left: Specification[T], right: Specification[T]):
        self.left = left
        self.right = right

    def to_expression(self) -> ColumnElement[bool]:
        return self.left.to_expression() | self.right.to_expression()


class NotSpecification(Specification[T]):
    """Logical NOT of a specification."""

    def __init__(self, spec: Specification[T]):
        self.spec = spec

    def to_expression(self) -> ColumnElement[bool]:
        return ~self.spec.to_expression()
