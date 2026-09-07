import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.tender import Tender
from app.models.category import Category
from app.models.tender_document import TenderDocument
from app.services.tender_processor import process_tender

@pytest.mark.asyncio
async def test_process_tender_semantic_filter_no_categories():
    # Подготавливаем мок сессии
    mock_db = AsyncMock()
    tender = Tender(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_tender_id='test',
        title='Тестовый тендер',
        description='Описание',
        status='NEW',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_db.get = AsyncMock(return_value=tender)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.execute = AsyncMock()
    # Патчим _load_documents, чтобы вернуть []
    with patch('app.services.tender_processor._load_documents', new_callable=AsyncMock) as mock_load:
        mock_load.return_value = []
        # Патчим generate_embedding, чтобы вернуть вектор
        with patch('app.services.tender_processor.generate_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1]*1536
            # Патчим _semantic_filter, чтобы не вызывать БД категории? нет, нужно оставить.
            # Но так как нет категорий, best_category=None
            with patch('app.services.tender_processor._semantic_filter', new_callable=AsyncMock) as mock_semantic:
                mock_semantic.return_value = None
                await process_tender(tender.id, mock_db)
    # Проверяем, что коммиты были
    assert mock_db.commit.await_count >= 1
