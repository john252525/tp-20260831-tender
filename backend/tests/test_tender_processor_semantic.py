import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.tender import Tender
from app.models.category import Category
from app.services.tender_processor import _semantic_filter

@pytest.mark.asyncio
async def test_semantic_filter_relevant():
    tender = Tender(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_tender_id='test',
        title='Поставка ноутбуков',
        description='Ноутбуки HP',
        status='PROCESSING',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    category = Category(
        id=uuid.uuid4(),
        name='Оргтехника',
        description='Компьютеры',
        keywords=['ноутбук'],
        embedding=[0.9]*1536,
    )
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [category]
    mock_db.execute = AsyncMock(return_value=mock_result)
    with patch('app.services.tender_processor.generate_embedding', new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.95]*1536
        with patch('app.services.tender_processor.cosine_similarity', new_callable=AsyncMock) as mock_cos:
            mock_cos.return_value = 0.9
            await _semantic_filter(tender, 'текст', mock_db)
    assert tender.status == 'RELEVANT'
    assert tender.matched_category_id == category.id
