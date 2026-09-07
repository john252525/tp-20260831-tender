import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import Response
from app.services.gosplan_client import GosPlanClient

@pytest.mark.asyncio
async def test_search_purchases_success():
    client = GosPlanClient()
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {'purchase_number': '123', 'object_info': 'Тест'}
    ]
    mock_response.raise_for_status = MagicMock()

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        results = await client.search_purchases(query='ноутбук')
    assert len(results) == 1
    assert results[0]['purchase_number'] == '123'

@pytest.mark.asyncio
async def test_get_purchase_documents():
    client = GosPlanClient()
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {'docs': [{'doc_type': 'contract'}]}
    mock_response.raise_for_status = MagicMock()

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        docs = await client.get_purchase_documents('123')
    assert len(docs) == 1
    assert docs[0]['doc_type'] == 'contract'
