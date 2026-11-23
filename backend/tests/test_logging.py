"""
Unit tests for Centralized Structured Logging Subsystem
"""

from app.core.logging import configure_logging, get_logger


def test_configure_logging_initialization():
    configure_logging()
    logger = get_logger("test_module")
    assert logger is not None


def test_logger_context_binding():
    logger = get_logger("context_test")
    bound_logger = logger.bind(
        correlation_id="test-corr-123", request_id="test-req-456"
    )
    assert bound_logger is not None
