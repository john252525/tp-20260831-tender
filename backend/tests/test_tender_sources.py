import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.models.tender_source import TenderSource
from app.models.task import Task

@pytest.mark.asyncio
async def test_sync_source_sets_celery(app_without_auth):
    source = TenderSource(
        id=uuid.uuid4(),
        name='Test',
        type='aggregator_api',
        api_url='https://example.com',
        api_key_encrypted='secret',
        config={},
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=source)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    with patch('app.api.v1.tender_sources.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        with patch('app.api.v1.tender_sources.sync_tenders_task.delay') as mock_delay:
            mock_delay.return_value = MagicMock(id='celery-id')
            transport = ASGITransport(app=app_without_auth)
            async with AsyncClient(transport=transport, base_url='http://test') as client:
                response = await client.post(f'/api/v1/tender-sources/{source.id}/sync')

    assert response.status_code == 202
    added_objects = [call.args[0] for call in mock_session.add.call_args_list]
    task_obj = next((obj for obj in added_objects if isinstance(obj, Task)), None)
    assert task_obj is not None
    mock_delay.assert_called_once_with(str(task_obj.id))
