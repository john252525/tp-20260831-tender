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
    # execute используется для подсчёта позиций при проверке обогащения
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    mock_db.execute = AsyncMock(return_value=count_result)
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


@pytest.mark.asyncio
async def test_embedding_failure_does_not_mark_tender_as_terminal_error():
    """Сбой сервиса эмбеддингов не должен переводить тендер в терминальный ERROR.

    Данные о закупке (позиции, описание) уже собраны, а недоступность
    Ollama — проблема инфраструктуры. Тендер оставляется в UNCERTAIN,
    чтобы его можно было обработать повторно.
    """
    mock_db = AsyncMock()
    tender = Tender(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_tender_id='test-embed-fail',
        title='Тестовый тендер',
        description='Описание закупки',
        status='NEW',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_db.get = AsyncMock(return_value=tender)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    mock_db.execute = AsyncMock(return_value=count_result)

    with patch('app.services.tender_processor._load_documents', new_callable=AsyncMock) as mock_load, \
         patch('app.services.tender_processor.generate_embedding', new_callable=AsyncMock) as mock_embed:
        mock_load.return_value = []
        mock_embed.side_effect = RuntimeError('ollama unavailable')
        await process_tender(tender.id, mock_db)

    assert tender.status == 'UNCERTAIN'
    assert tender.status != 'ERROR'
    assert 'повторная обработка' in (tender.processing_error or '')
    assert tender.similarity_score is None


@pytest.mark.asyncio
async def test_existing_positions_are_not_overwritten_by_llm():
    """Позиции из API ГосПлан не должны затираться LLM-извлечением."""
    mock_db = AsyncMock()
    tender = Tender(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_tender_id='test-keep-positions',
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

    # execute используется для подсчёта позиций и поиска категорий
    positions_count_result = MagicMock()
    positions_count_result.scalar_one.return_value = 3  # позиции уже есть
    mock_db.execute = AsyncMock(return_value=positions_count_result)

    with patch('app.services.tender_processor._load_documents', new_callable=AsyncMock) as mock_load, \
         patch('app.services.tender_processor.generate_embedding', new_callable=AsyncMock) as mock_embed, \
         patch('app.services.tender_processor._extract_tender_structure', new_callable=AsyncMock) as mock_extract, \
         patch('app.services.tender_processor.calculate_score', new_callable=AsyncMock) as mock_score:
        mock_load.return_value = []
        mock_embed.return_value = [0.1] * 768
        mock_score.return_value = (75.0, {'margin_score': 50.0})
        tender.status = 'RELEVANT'
        await process_tender(tender.id, mock_db)

    # LLM-извлечение структуры не должно запускаться, если позиции уже есть
    mock_extract.assert_not_awaited()


@pytest.mark.asyncio
async def test_approved_tender_is_not_reprocessed():
    """Решение человека неприкосновенно: APPROVED не переобрабатывается.

    Автооркестрация могла взять одобренный тендер и перезатереть статус
    на PROCESSING, потеряв решение человека.
    """
    mock_db = AsyncMock()
    tender = Tender(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_tender_id='test-approved',
        title='Одобренный тендер',
        description='Описание',
        status='APPROVED',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_db.get = AsyncMock(return_value=tender)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.execute = AsyncMock()

    await process_tender(tender.id, mock_db)

    assert tender.status == 'APPROVED'
    # Ни история переходов, ни обработка не запускались
    assert mock_db.add.call_count == 0
    assert mock_db.commit.await_count == 0


@pytest.mark.asyncio
async def test_rejected_tender_is_not_reprocessed():
    """Отклонённый тендер также не переобрабатывается автоматикой."""
    mock_db = AsyncMock()
    tender = Tender(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_tender_id='test-rejected',
        title='Отклонённый тендер',
        description='Описание',
        status='REJECTED',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_db.get = AsyncMock(return_value=tender)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.execute = AsyncMock()

    await process_tender(tender.id, mock_db)

    assert tender.status == 'REJECTED'
    assert mock_db.add.call_count == 0
