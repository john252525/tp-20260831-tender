import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.models.commercial_offer import CommercialOffer
from app.models.task import Task

@pytest.mark.asyncio
async def test_reparse_offer_sets_celery(app_without_auth):
    offer = CommercialOffer(
        id=uuid.uuid4(),
        lot_supplier_id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        status='PROCESSING',
    )
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=offer)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    with patch('app.api.v1.commercial_offers.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        with patch('app.api.v1.commercial_offers.parse_cp_task.delay') as mock_delay:
            mock_delay.return_value = MagicMock(id='celery-id')
            transport = ASGITransport(app=app_without_auth)
            async with AsyncClient(transport=transport, base_url='http://test') as client:
                response = await client.post(f'/api/v1/commercial-offers/{offer.id}/reparse')

    assert response.status_code == 202
    added_objects = [call.args[0] for call in mock_session.add.call_args_list]
    task_obj = next((obj for obj in added_objects if isinstance(obj, Task)), None)
    assert task_obj is not None
    mock_delay.assert_called_once_with(str(task_obj.id))
