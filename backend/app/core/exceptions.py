"""
Platform Database Exception Hierarchy

Provides custom, strongly typed database exceptions wrapping SQLAlchemy and
asyncpg driver errors into standard platform errors.
"""


class DatabaseError(Exception):
    """Base exception for all database platform errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection acquisition fails."""


class RecordNotFoundError(DatabaseError):
    """Raised when a requested database entity is not found."""


class DuplicateKeyError(DatabaseError):
    """Raised when a unique constraint or primary key violation occurs."""


class OptimisticLockError(DatabaseError):
    """Raised when concurrent update fails due to version_id mismatch."""


class TransactionError(DatabaseError):
    """Raised when transaction commit or rollback fails."""


class DatabaseConstraintError(DatabaseError):
    """Raised when foreign key or check constraint is violated."""


class DomainValidationError(Exception):
    """Raised when domain rule or state machine validation fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


# Security Exception Hierarchy
class SecurityError(Exception):
    """Base exception for all platform security and authentication errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(SecurityError):
    """Raised when authentication credentials or headers are missing/invalid."""


class InvalidTokenError(SecurityError):
    """Raised when JWT signature, structure, or claims validation fails."""


class ExpiredTokenError(SecurityError):
    """Raised when JWT token timestamp has expired."""


class RevokedTokenError(SecurityError):
    """Raised when JWT token JTI has been revoked in blacklist."""


class AuthorizationForbiddenError(SecurityError):
    """Raised when access is forbidden for the current auth_stage or permissions."""

