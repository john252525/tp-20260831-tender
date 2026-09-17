import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.tender import Tender
from app.services.tender_processor import process_tender

@pytest.mark.asyncio
async def test_process_tender_uploads_document_to_s3():
    tender_id = uuid.uuid4()
    source_id = uuid.uuid4()
    tender = Tender(
        id=tender_id,
        source_id=source_id,
        source_tender_id='test',
        title='Тест',
        description='',
        status='NEW',
        source_url='https://example.com/test.pdf',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_db = AsyncMock()
    # get вызывается и для тендера, и для источника (при автообогащении)
    mock_db.get = AsyncMock(side_effect=lambda model, pk: tender if model is Tender else None)

    # Первый execute — проверка наличия позиций при автообогащении
    positions_count_result = MagicMock()
    positions_count_result.scalar_one.return_value = 0
    # Второй execute — поиск существующих документов в _load_documents
    existing_docs_result = MagicMock()
    existing_docs_result.scalars().all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[positions_count_result, existing_docs_result])

    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Фейковый ответ HTTP
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.content = b'%PDF-1.4 test'

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_http_get:
        mock_http_get.return_value = fake_response
        with patch('app.services.tender_processor.s3_service.upload_bytes', new_callable=AsyncMock) as mock_upload, \
             patch('app.services.tender_processor.s3_service.download_bytes', new_callable=AsyncMock) as mock_download, \
             patch('app.services.tender_processor._semantic_filter', new_callable=AsyncMock) as mock_semantic, \
             patch('app.services.tender_processor._extract_tender_structure', new_callable=AsyncMock) as mock_extract:
            mock_upload.return_value = (True, 'tenders/test/test.pdf')
            mock_download.return_value = b'fake content'
            mock_semantic.return_value = None
            mock_extract.return_value = None

            await process_tender(tender_id, mock_db)

    # Проверяем, что загрузка в S3 была вызвана один раз
    mock_upload.assert_called_once()
    # Проверяем, что в сессию был добавлен TenderDocument с storage_path
    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    doc = next((obj for obj in added_objects if obj.__class__.__name__ == 'TenderDocument'), None)
    assert doc is not None
    assert doc.storage_path == 'tenders/test/test.pdf'
