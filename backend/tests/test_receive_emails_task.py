import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.workers.tasks import receive_emails_task

def test_receive_emails_task_uploads_attachments():
    # Подготовка тестовых данных
    attachment = {
        'filename': 'kp.xlsx',
        'content': b'file-bytes',
        'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }
    message = {
        'message_id': '<incoming@example.com>',
        'in_reply_to': '<outgoing@example.com>',
        'from': 'supplier@example.com',
        'subject': 'КП',
        'body_text': 'Цены в приложении',
        'attachments': [attachment],
    }

    # Мокаем сессию БД
    session = AsyncMock()
    supplier = MagicMock()
    supplier.id = uuid.uuid4()
    supplier.email = 'supplier@example.com'

    lot = MagicMock()
    lot.id = uuid.uuid4()
    lot.tender_id = uuid.uuid4()
    lot.supplier_id = supplier.id

    # Настраиваем последовательность execute:
    # 1) поиск Communication по In-Reply-To -> None
    # 2) поиск Supplier по email -> supplier
    # 3) поиск LotSupplier -> lot
    session.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=supplier)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=lot)),
    ])
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock()

    # Мокаем AsyncSessionLocal
    with patch('app.workers.tasks.AsyncSessionLocal') as mock_session_local:
        mock_session_local.return_value.__aenter__.return_value = session

        # Мокаем receive_emails
        with patch('app.workers.tasks.receive_emails', new_callable=AsyncMock) as mock_receive:
            mock_receive.return_value = [message]

            # Мокаем s3_service.upload_bytes
            with patch('app.workers.tasks.s3_service.upload_bytes', new_callable=AsyncMock) as mock_upload:
                mock_upload.return_value = (True, 'communications/test/kp.xlsx')

                # Мокаем parse_cp_task.delay, чтобы не обращаться к брокеру
                with patch('app.workers.tasks.parse_cp_task.delay') as mock_delay:
                    mock_delay.return_value = MagicMock(id='celery-task-id')

                    # Вызываем задачу
                    receive_emails_task()

    # Проверяем, что receive_emails вызвана один раз
    mock_receive.assert_called_once()

    # Проверяем вызов s3_service.upload_bytes
    mock_upload.assert_called_once()
    call_kwargs = mock_upload.call_args[1]
    assert call_kwargs['content'] == b'file-bytes'
    assert 'kp.xlsx' in call_kwargs['key']

    # Проверяем, что в сессию были добавлены все необходимые объекты
    added_objects = [call.args[0] for call in session.add.call_args_list]
    classes = [obj.__class__.__name__ for obj in added_objects]
    assert 'Communication' in classes
    assert 'CommunicationAttachment' in classes
    assert 'CommercialOffer' in classes
    assert 'Task' in classes

    # Проверяем, что parse_cp_task.delay был вызван один раз
    mock_delay.assert_called_once()
