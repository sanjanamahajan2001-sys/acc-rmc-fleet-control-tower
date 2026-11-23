"""
Unit tests for Shared FastAPI Dependencies
"""

import pytest

from app.core.context import RequestContext
from app.core.unit_of_work import UnitOfWork
from app.dependencies.common import get_current_request_context, get_uow


def test_get_current_request_context_dependency():
    ctx = get_current_request_context()
    assert ctx == RequestContext


@pytest.mark.asyncio
async def test_get_uow_dependency_yields_unit_of_work():
    gen = get_uow()
    uow = await gen.__anext__()
    assert isinstance(uow, UnitOfWork)
    await gen.aclose()
