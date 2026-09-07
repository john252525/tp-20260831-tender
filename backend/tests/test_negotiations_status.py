import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.models.tender import Tender
from app.services.negotiation_service import get_negotiation_status

@pytest.mark.asyncio
async def test_get_negotiation_status_empty(app_without_auth):
    tender_id = uuid.uuid4()
    tender = Tender(id=tender_id, source_id=uuid.uuid4(), source_tender_id='stub', title='Test', description='', status='SCORED')
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=tender)
    # Мокаем task_result: вернём None
    task_result = MagicMock()
    task_result.scalar_one_or_none.return_value = None
    # Мокаем lots_result: пустой
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = []
    mock_session.execute.side_effect = [task_result, lots_result]

    with patch('app.api.v1.negotiations.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get(f'/api/v1/tenders/{tender_id}/negotiation-status')

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['data']['status'] == 'COMPLETED'
    assert data['data']['suppliers'] == []
