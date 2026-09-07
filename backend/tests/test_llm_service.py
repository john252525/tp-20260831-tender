import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.llm_service import extract_structured_data, classify_incoming_email

@pytest.mark.asyncio
async def test_extract_structured_data_success():
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"positions": [], "requirements": {}}'))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch('app.services.llm_service._get_client', new_callable=AsyncMock) as mock_get_client:
        mock_get_client.return_value = mock_client
        data = await extract_structured_data('Тестовый текст')
    assert data == {'positions': [], 'requirements': {}}

@pytest.mark.asyncio
async def test_extract_structured_data_no_key():
    with patch('app.services.llm_service.settings.llm_api_key', ''):
        with pytest.raises(RuntimeError):
            await extract_structured_data('Тест')

@pytest.mark.asyncio
async def test_classify_incoming_email_no_key():
    with patch('app.services.llm_service.settings.llm_api_key', ''):
        result = await classify_incoming_email('Тема', 'Тело')
        assert result == 'other'
