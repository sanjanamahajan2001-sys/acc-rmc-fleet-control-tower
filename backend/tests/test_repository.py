"""
Unit tests for Generic Async Repository Base
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import RecordNotFoundError
from app.models.base import VersionedEntity
from app.repositories.base import GenericRepository
from app.repositories.pagination import PageRequest
from app.repositories.specification import Specification


class SampleEntity(VersionedEntity):
    __tablename__ = "sample_test_entities"


class SampleSpec(Specification[SampleEntity]):
    def to_expression(self):
        return SampleEntity.is_deleted == False


@pytest.mark.asyncio
async def test_repository_get_by_id_success():
    mock_session = AsyncMock()
    sample_id = uuid.uuid4()
    entity = SampleEntity(id=sample_id)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = entity
    mock_session.execute.return_value = mock_result

    repo = GenericRepository(SampleEntity, mock_session)
    result = await repo.get_by_id(sample_id)
    assert result.id == sample_id


@pytest.mark.asyncio
async def test_repository_get_by_id_not_found():
    mock_session = AsyncMock()
    sample_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    repo = GenericRepository(SampleEntity, mock_session)
    with pytest.raises(RecordNotFoundError):
        await repo.get_by_id(sample_id)


@pytest.mark.asyncio
async def test_repository_find_with_pagination_and_spec():
    mock_session = AsyncMock()
    entity1 = SampleEntity(id=uuid.uuid4())
    entity2 = SampleEntity(id=uuid.uuid4())

    mock_count_res = MagicMock()
    mock_count_res.scalar_one.return_value = 2

    mock_items_res = MagicMock()
    mock_items_res.scalars().all.return_value = [entity1, entity2]

    mock_session.execute.side_effect = [mock_count_res, mock_items_res]

    repo = GenericRepository(SampleEntity, mock_session)
    page_req = PageRequest(page=1, size=10, sort_by="id", sort_order="ASC")
    page = await repo.find(spec=SampleSpec(), page_request=page_req)

    assert page.total_elements == 2
    assert len(page.items) == 2


@pytest.mark.asyncio
async def test_repository_crud_operations():
    mock_session = AsyncMock()
    repo = GenericRepository(SampleEntity, mock_session)

    entity = SampleEntity(id=uuid.uuid4())
    await repo.create(entity)
    mock_session.add.assert_called_once_with(entity)
    mock_session.flush.assert_awaited()

    await repo.create_many([entity])
    mock_session.add_all.assert_called_once()

    await repo.update(entity)

    # Soft delete test
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = entity
    mock_session.execute.return_value = mock_result

    await repo.soft_delete(entity.id)
    assert entity.is_deleted is True
    assert entity.deleted_at is not None

    # Hard delete test
    await repo.hard_delete(entity.id)
    mock_session.delete.assert_called_once_with(entity)
