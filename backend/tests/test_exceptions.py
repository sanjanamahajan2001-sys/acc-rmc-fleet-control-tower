"""
Unit tests for Database Exception Hierarchy
"""

from app.core.exceptions import (
    DatabaseError,
    OptimisticLockError,
    RecordNotFoundError,
)


def test_database_exception_hierarchy():
    err = RecordNotFoundError("Record not found", details={"entity_id": "123"})
    assert isinstance(err, DatabaseError)
    assert err.message == "Record not found"
    assert err.details["entity_id"] == "123"


def test_optimistic_lock_exception():
    err = OptimisticLockError(
        "Version mismatch", details={"expected_version": 1, "actual_version": 2}
    )
    assert isinstance(err, DatabaseError)
    assert err.details["expected_version"] == 1
