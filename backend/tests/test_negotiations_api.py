import pytest
import uuid
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_start_negotiation_not_found(app_without_auth):
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)

    with patch('app.api.v1.negotiations.get_db') as mock_get_db:
        mock_get_db.return_value = mock_session
        transport = ASGITransport(app=app_without_auth)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post(f'/api/v1/tenders/{uuid.uuid4()}/negotiate', json={'action': 'request_clarification'})
    assert response.status_code == 404
