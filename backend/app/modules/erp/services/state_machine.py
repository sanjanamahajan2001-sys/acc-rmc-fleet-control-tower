"""
ImportJob State Machine Definition & Valid State Transition Controls
"""

from enum import Enum

from app.core.exceptions import DomainValidationError


class ImportJobState(str, Enum):
    QUEUED = "QUEUED"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    READY_FOR_PROCESSING = "READY_FOR_PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RESUMABLE = "RESUMABLE"
    DLQ = "DLQ"


# Allowed state transitions dictionary
VALID_TRANSITIONS: dict[ImportJobState, set[ImportJobState]] = {
    ImportJobState.QUEUED: {
        ImportJobState.UPLOADING,
        ImportJobState.CANCELLED,
        ImportJobState.FAILED,
    },
    ImportJobState.UPLOADING: {
        ImportJobState.UPLOADED,
        ImportJobState.RESUMABLE,
        ImportJobState.CANCELLED,
        ImportJobState.FAILED,
    },
    ImportJobState.RESUMABLE: {
        ImportJobState.UPLOADING,
        ImportJobState.CANCELLED,
        ImportJobState.FAILED,
    },
    ImportJobState.UPLOADED: {
        ImportJobState.READY_FOR_PROCESSING,
        ImportJobState.CANCELLED,
        ImportJobState.FAILED,
    },
    ImportJobState.READY_FOR_PROCESSING: {
        ImportJobState.QUEUED,
        ImportJobState.COMPLETED,
        ImportJobState.FAILED,
        ImportJobState.CANCELLED,
        ImportJobState.DLQ,
    },
    ImportJobState.FAILED: {
        ImportJobState.QUEUED,
        ImportJobState.RESUMABLE,
        ImportJobState.DLQ,
        ImportJobState.CANCELLED,
    },
    ImportJobState.CANCELLED: {ImportJobState.QUEUED},
    ImportJobState.DLQ: {ImportJobState.QUEUED},
}


class ImportStateMachine:
    """
    Guarantees strict state transitions for ImportJob lifecycle.
    Prevents invalid operational state jumps.
    """

    @staticmethod
    def validate_transition(current_state: str, target_state: str) -> None:
        try:
            curr_enum = ImportJobState(current_state)
            target_enum = ImportJobState(target_state)
        except ValueError as e:
            raise DomainValidationError(f"Invalid import job status value: {e}") from e

        allowed = VALID_TRANSITIONS.get(curr_enum, set())
        if target_enum not in allowed:
            raise DomainValidationError(
                f"Cannot transition ImportJob from '{current_state}' to '{target_state}'. "
                f"Allowed transitions from '{current_state}': {[s.value for s in allowed]}"
            )
