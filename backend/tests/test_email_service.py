import pytest
from unittest.mock import patch
from app.services.email_service import send_email, receive_emails

@pytest.mark.asyncio
async def test_send_email_no_config():
    with patch('app.services.email_service.settings.smtp_host', ''):
        success, message_id = await send_email('test@example.com', 'Subject', 'Body')
        assert success is False
        assert message_id == ''

@pytest.mark.asyncio
async def test_receive_emails_no_config():
    with patch('app.services.email_service.settings.imap_host', ''):
        messages = await receive_emails()
        assert messages == []
