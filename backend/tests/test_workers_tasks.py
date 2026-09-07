import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.workers.tasks import (
    process_tender_task, sync_tenders_task, search_suppliers_task,
    send_communications_task, parse_cp_task, receive_emails_task, negotiate_task,
    normalize_message_id
)

# Smoke-тесты: проверяем, что функции определены и могут быть вызваны с замоканными зависимостями.
# Реальное выполнение Celery-задач не тестируется.

def test_normalize_message_id():
    assert normalize_message_id('<abc@example.com>') == 'abc@example.com'
    assert normalize_message_id('  <abc@example.com>  ') == 'abc@example.com'
    assert normalize_message_id('abc@example.com') == 'abc@example.com'
    assert normalize_message_id('') == ''

def test_send_communications_task_smoke():
    with patch('app.workers.tasks.AsyncSessionLocal') as mock_session_local, \
         patch('app.workers.tasks._get_task', new_callable=AsyncMock) as mock_get_task, \
         patch('app.workers.tasks._update_task', new_callable=AsyncMock) as mock_update_task:
        # Настраиваем async context manager для AsyncSessionLocal
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=None)

        # Мокаем задачу: entity_id будет uuid
        mock_task = MagicMock()
        mock_task.entity_id = uuid.uuid4()
        mock_get_task.return_value = mock_task

        # Вызываем задачу синхронно (asyncio.run внутри не запустится, так как тест не в event loop)
        send_communications_task('task-id')

        # Проверяем, что _update_task вызывался хотя бы дважды (IN_PROGRESS и COMPLETED)
        assert mock_update_task.await_count >= 2

def test_parse_cp_task_smoke():
    with patch('app.workers.tasks.AsyncSessionLocal') as mock_session_local, \
         patch('app.workers.tasks._get_task', new_callable=AsyncMock) as mock_get_task, \
         patch('app.workers.tasks._update_task', new_callable=AsyncMock) as mock_update_task, \
         patch('app.workers.tasks.parse_cp', new_callable=AsyncMock) as mock_parse_cp:
        # Настраиваем async context manager для AsyncSessionLocal
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=None)

        # Мокаем задачу: entity_id будет uuid
        mock_task = MagicMock()
        mock_task.entity_id = uuid.uuid4()
        mock_get_task.return_value = mock_task

        # Парсер возвращает True
        mock_parse_cp.return_value = True

        # Вызываем задачу синхронно
        parse_cp_task('task-id')

        # Проверяем, что _update_task вызывался хотя бы дважды
        assert mock_update_task.await_count >= 2
