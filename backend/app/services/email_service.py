import asyncio
import email
import smtplib
import imaplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import decode_header
from email.utils import make_msgid
from typing import List, Dict, Any, Optional, Tuple
import structlog

from app.core.config import settings
from app.services.s3_service import s3_service

logger = structlog.get_logger()

async def _get_email_settings(db=None):
    """Загружает настройки SMTP/IMAP из БД (раздел communication), при отсутствии БД использует .env."""
    if db is not None:
        from app.services.settings_service import get_section_settings
        from app.services.encryption_service import encryption_service
        comm_settings = await get_section_settings(db, 'communication')
        email_config = comm_settings.get('email_config', {})
        smtp_host = email_config.get('smtp_host', settings.smtp_host)
        smtp_port = email_config.get('smtp_port', settings.smtp_port)
        smtp_user = email_config.get('smtp_user', settings.smtp_user)
        # Пароли могут быть зашифрованы; расшифровываем только если значение непустое и похоже на Fernet-токен
        smtp_password = email_config.get('smtp_password_encrypted', settings.smtp_password)
        if smtp_password and smtp_password.startswith('gAAAA'):
            smtp_password = encryption_service.decrypt(smtp_password)
        smtp_use_tls = email_config.get('smtp_use_tls', settings.smtp_use_tls)
        imap_host = email_config.get('imap_host', settings.imap_host)
        imap_port = email_config.get('imap_port', settings.imap_port)
        imap_user = email_config.get('imap_user', settings.imap_user)
        imap_password = email_config.get('imap_password_encrypted', settings.imap_password)
        if imap_password and imap_password.startswith('gAAAA'):
            imap_password = encryption_service.decrypt(imap_password)
        imap_use_ssl = email_config.get('imap_use_ssl', settings.imap_use_ssl)
        return {
            'smtp_host': smtp_host,
            'smtp_port': smtp_port,
            'smtp_user': smtp_user,
            'smtp_password': smtp_password,
            'smtp_use_tls': smtp_use_tls,
            'imap_host': imap_host,
            'imap_port': imap_port,
            'imap_user': imap_user,
            'imap_password': imap_password,
            'imap_use_ssl': imap_use_ssl,
        }
    else:
        return {
            'smtp_host': settings.smtp_host,
            'smtp_port': settings.smtp_port,
            'smtp_user': settings.smtp_user,
            'smtp_password': settings.smtp_password,
            'smtp_use_tls': settings.smtp_use_tls,
            'imap_host': settings.imap_host,
            'imap_port': settings.imap_port,
            'imap_user': settings.imap_user,
            'imap_password': settings.imap_password,
            'imap_use_ssl': settings.imap_use_ssl,
        }

async def send_email(
    to_address: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    attachments: List[Dict[str, bytes]] = None,
    db=None,
) -> Tuple[bool, str]:
    """Отправляет email через SMTP. Возвращает (успех, message_id).
    Настройки берутся из БД, если передан db, иначе из .env.
    """
    email_settings = await _get_email_settings(db)
    smtp_host = email_settings['smtp_host']
    smtp_user = email_settings['smtp_user']
    if not smtp_host or not smtp_user:
        logger.warning('email_service.smtp_not_configured')
        return False, ''

    msg = MIMEMultipart('mixed')
    msg['From'] = smtp_user
    msg['To'] = to_address
    msg['Subject'] = subject
    message_id = make_msgid(domain=smtp_host)
    msg['Message-ID'] = message_id

    text_part = MIMEText(body_text, 'plain', 'utf-8')
    msg.attach(text_part)
    if body_html:
        html_part = MIMEText(body_html, 'html', 'utf-8')
        msg.attach(html_part)
    if attachments:
        for attachment in attachments:
            part = MIMEApplication(attachment['content'], _subtype=attachment.get('mime_type', 'application/octet-stream'))
            part.add_header('Content-Disposition', 'attachment', filename=attachment['filename'])
            msg.attach(part)

    def _send_sync():
        try:
            if email_settings['smtp_use_tls']:
                server = smtplib.SMTP(smtp_host, email_settings['smtp_port'])
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(smtp_host, email_settings['smtp_port'])
            server.login(smtp_user, email_settings['smtp_password'])
            server.sendmail(smtp_user, [to_address], msg.as_string())
            server.quit()
            return message_id
        except Exception as exc:
            logger.error('email_service.send_sync_failed', to=to_address, error=str(exc))
            return ''

    try:
        result_message_id = await asyncio.to_thread(_send_sync)
        if result_message_id:
            logger.info('email_service.sent', to=to_address, subject=subject, message_id=result_message_id)
            return True, result_message_id
        return False, ''
    except Exception as exc:
        logger.error('email_service.send_failed', to=to_address, error=str(exc))
        return False, ''

async def receive_emails(
    folder: str = 'INBOX',
    mark_as_read: bool = False,
    since_days: int = 1,
    db=None,
) -> List[Dict[str, Any]]:
    """Получает непрочитанные письма через IMAP. Настройки из БД при наличии db."""
    email_settings = await _get_email_settings(db)
    imap_host = email_settings['imap_host']
    imap_user = email_settings['imap_user']
    if not imap_host or not imap_user:
        logger.warning('email_service.imap_not_configured')
        return []

    def _receive_sync():
        messages = []
        try:
            if email_settings['imap_use_ssl']:
                client = imaplib.IMAP4_SSL(imap_host, email_settings['imap_port'])
            else:
                client = imaplib.IMAP4(imap_host, email_settings['imap_port'])
            client.login(imap_user, email_settings['imap_password'])
            client.select(folder)

            since_date = time.strftime('%d-%b-%Y', time.gmtime(time.time() - since_days * 86400))
            status, data = client.search(None, f'(UNSEEN SINCE {since_date})')
            if status != 'OK':
                client.logout()
                return messages

            for num in data[0].split():
                status, msg_data = client.fetch(num, '(RFC822)')
                if status != 'OK':
                    continue
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject = ''
                if msg['Subject']:
                    decoded = decode_header(msg['Subject'])
                    subject = ''.join([part.decode(enc or 'utf-8') if isinstance(part, bytes) else part for part, enc in decoded])

                body_text = ''
                attachments = []
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == 'text/plain':
                            body_text = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                        elif content_type == 'text/html':
                            continue
                        elif part.get_filename():
                            filename = part.get_filename()
                            content = part.get_payload(decode=True)
                            attachments.append({'filename': filename, 'content': content, 'mime_type': content_type, 'storage_path': None})
                else:
                    body_text = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')

                messages.append({
                    'message_id': msg['Message-ID'],
                    'in_reply_to': msg['In-Reply-To'],
                    'from': msg['From'],
                    'subject': subject,
                    'body_text': body_text,
                    'attachments': attachments,
                    'received_at': msg['Date'],
                })

                if mark_as_read:
                    client.store(num, '+FLAGS', '\\Seen')

            client.close()
            client.logout()
        except Exception as exc:
            logger.error('email_service.receive_sync_failed', error=str(exc))
        return messages

    try:
        return await asyncio.to_thread(_receive_sync)
    except Exception as exc:
        logger.error('email_service.receive_failed', error=str(exc))
        return []
