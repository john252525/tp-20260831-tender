import asyncio
import re
from datetime import datetime, timezone
from uuid import UUID

from app.workers.celery_app import celery_app
from celery import Task  # noqa
import structlog
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.models.task import Task
from app.models.tender import Tender
from app.models.tender_position import TenderPosition
from app.models.lot_supplier import LotSupplier
from app.models.supplier import Supplier
from app.models.communication import Communication, CommunicationAttachment
from app.models.commercial_offer import CommercialOffer

from app.services.tender_processor import process_tender
from app.services.tender_sync_service import sync_tenders_from_source
from app.services.supplier_search import search_suppliers_for_tender
from app.services.cp_parser import parse_cp
from app.services.email_service import receive_emails, send_email
from app.services.template_rendering import render_template, build_cp_context
from app.services.settings_service import get_section_settings
from app.services.file_generator import generate_positions_excel
from app.services.s3_service import s3_service

logger = structlog.get_logger()

async def _get_task(task_id: str, session):
    return await session.get(Task, UUID(task_id))

async def _update_task(task_id: str, **kwargs):
    async with AsyncSessionLocal() as session:
        task = await _get_task(task_id, session)
        if task:
            for key, value in kwargs.items():
                setattr(task, key, value)
            await session.commit()

def normalize_message_id(msg_id: str) -> str:
    if not msg_id:
        return ''
    return msg_id.strip().strip('<>').strip()

@celery_app.task
def process_tender_task(task_id: str):
    async def _run():
        await _update_task(task_id, status='IN_PROGRESS', started_at=datetime.now(timezone.utc))
        try:
            async with AsyncSessionLocal() as session:
                task = await _get_task(task_id, session)
                if not task or not task.entity_id:
                    raise ValueError('Task or entity_id not found')
                tender_id = task.entity_id
                await process_tender(tender_id, session)
            await _update_task(task_id, status='COMPLETED', progress_percent=100.0, completed_at=datetime.now(timezone.utc), result_summary='Тендер обработан')
        except Exception as exc:
            logger.error('celery.process_tender_failed', task_id=task_id, error=str(exc))
            await _update_task(task_id, status='FAILED', error_message=str(exc), completed_at=datetime.now(timezone.utc))
    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()
    asyncio.run(_runner())

@celery_app.task
def sync_tenders_task(task_id: str):
    async def _run():
        await _update_task(task_id, status='IN_PROGRESS', started_at=datetime.now(timezone.utc))
        try:
            async with AsyncSessionLocal() as session:
                task = await _get_task(task_id, session)
                if not task or not task.entity_id:
                    raise ValueError('Task or entity_id not found')
                source_id = task.entity_id
                created = await sync_tenders_from_source(source_id, session)
                # Автозапуск обработки новых тендеров
                for tender in created:
                    process_task = Task(
                        task_type='PROCESS_TENDER',
                        status='PENDING',
                        entity_type='tender',
                        entity_id=tender.id,
                        progress_percent=0.0,
                        input_data={'tender_id': str(tender.id)}
                    )
                    session.add(process_task)
                    await session.flush()
                    celery_proc = process_tender_task.delay(str(process_task.id))
                    process_task.celery_task_id = celery_proc.id
            await _update_task(task_id, status='COMPLETED', progress_percent=100.0, completed_at=datetime.now(timezone.utc), result_summary=f'Импортировано: {len(created)}')
        except Exception as exc:
            logger.error('celery.sync_tenders_failed', task_id=task_id, error=str(exc))
            await _update_task(task_id, status='FAILED', error_message=str(exc), completed_at=datetime.now(timezone.utc))
    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()
    asyncio.run(_runner())

@celery_app.task
def search_suppliers_task(task_id: str):
    async def _run():
        await _update_task(task_id, status='IN_PROGRESS', started_at=datetime.now(timezone.utc))
        try:
            async with AsyncSessionLocal() as session:
                task = await _get_task(task_id, session)
                if not task or not task.entity_id:
                    raise ValueError('Task or entity_id not found')
                tender_id = task.entity_id
                input_data = task.input_data or {}
                results = await search_suppliers_for_tender(
                    tender_id=tender_id,
                    max_suppliers=input_data.get('max_suppliers', 10),
                    channels=input_data.get('channels', ['google','internal_db']),
                    priority_order=input_data.get('priority_order', ['manufacturer','distributor','wholesaler']),
                    db=session
                )
            await _update_task(task_id, status='COMPLETED', progress_percent=100.0, completed_at=datetime.now(timezone.utc), result_summary=f"Найдено: {len(results['results'])}", output_data=results)
        except Exception as exc:
            logger.error('celery.search_suppliers_failed', task_id=task_id, error=str(exc))
            await _update_task(task_id, status='FAILED', error_message=str(exc), completed_at=datetime.now(timezone.utc))
    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()
    asyncio.run(_runner())

@celery_app.task
def send_communications_task(task_id: str):
    async def _run():
        await _update_task(task_id, status='IN_PROGRESS', started_at=datetime.now(timezone.utc))
        try:
            async with AsyncSessionLocal() as session:
                task = await _get_task(task_id, session)
                if not task or not task.entity_id:
                    raise ValueError('Task or entity_id not found')
                tender_id = task.entity_id
                input_data = task.input_data or {}
                tender = await session.get(Tender, tender_id)
                if not tender:
                    raise ValueError('Тендер не найден')

                lot_query = select(LotSupplier).where(LotSupplier.tender_id == tender_id)
                if input_data.get('supplier_ids'):
                    supplier_ids = [UUID(sid) for sid in input_data['supplier_ids']]
                    lot_query = lot_query.where(LotSupplier.supplier_id.in_(supplier_ids))
                lots = (await session.execute(lot_query)).scalars().all()

                if not lots:
                    await _update_task(task_id, status='COMPLETED', progress_percent=100.0, completed_at=datetime.now(timezone.utc), result_summary='Нет привязанных поставщиков')
                    return

                templates_settings = await get_section_settings(session, 'templates') or {}
                cp_template = templates_settings.get('cp_request', {})
                override = input_data.get('template_override') or {}
                subject_template = override.get('subject') or cp_template.get('subject', 'Запрос КП: {lot_name}')
                body_template = override.get('body') or cp_template.get('body', '')

                context = await build_cp_context(tender, session)

                excel_content = None
                if input_data.get('attach_positions_table', True):
                    positions = (await session.execute(select(TenderPosition).where(TenderPosition.tender_id == tender_id))).scalars().all()
                    excel_content = await generate_positions_excel(positions)

                sent_count = 0
                failed_count = 0
                for lot in lots:
                    supplier = await session.get(Supplier, lot.supplier_id)
                    if not supplier or not supplier.email:
                        continue
                    subject = await render_template(subject_template, context)
                    body = await render_template(body_template, context)

                    attachments = []
                    if excel_content:
                        attachments.append({
                            'filename': 'positions.xlsx',
                            'content': excel_content,
                            'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        })

                    sent, message_id = await send_email(
                        to_address=supplier.email,
                        subject=subject,
                        body_text=body,
                        attachments=attachments,
                        db=session,
                    )
                    if not sent or not message_id:
                        failed_count += 1
                        logger.warning('celery.send_communications.email_not_sent', supplier_id=str(supplier.id))
                        continue

                    comm = Communication(
                        lot_supplier_id=lot.id,
                        tender_id=tender_id,
                        direction='outgoing',
                        channel='email',
                        subject=subject,
                        body_text=body,
                        message_type='cp_request',
                        external_id=message_id,
                        sent_at=datetime.now(timezone.utc),
                    )
                    session.add(comm)
                    lot.status = 'CP_REQUESTED'
                    session.add(lot)
                    sent_count += 1

                await session.commit()
                result_summary = f'Отправлено запросов КП: {sent_count}'
                if failed_count:
                    result_summary += f', неудач: {failed_count}'
                await _update_task(task_id, status='COMPLETED', progress_percent=100.0, completed_at=datetime.now(timezone.utc), result_summary=result_summary)
        except Exception as exc:
            logger.error('celery.send_communications_failed', task_id=task_id, error=str(exc))
            await _update_task(task_id, status='FAILED', error_message=str(exc), completed_at=datetime.now(timezone.utc))
    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()
    asyncio.run(_runner())

@celery_app.task
def parse_cp_task(task_id: str):
    async def _run():
        await _update_task(task_id, status='IN_PROGRESS', started_at=datetime.now(timezone.utc))
        try:
            async with AsyncSessionLocal() as session:
                task = await _get_task(task_id, session)
                if not task or not task.entity_id:
                    raise ValueError('Task or entity_id not found')
                cp_id = task.entity_id
                success = await parse_cp(cp_id, session)
                if not success:
                    raise RuntimeError('Парсинг не удался')
            await _update_task(task_id, status='COMPLETED', progress_percent=100.0, completed_at=datetime.now(timezone.utc), result_summary='КП распарсено')
        except Exception as exc:
            logger.error('celery.parse_cp_failed', task_id=task_id, error=str(exc))
            await _update_task(task_id, status='FAILED', error_message=str(exc), completed_at=datetime.now(timezone.utc))
    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()
    asyncio.run(_runner())

@celery_app.task
def receive_emails_task():
    async def _run():
        async with AsyncSessionLocal() as session:
            messages = await receive_emails(db=session)
            logger.info('celery.receive_emails_done', count=len(messages))
            for msg in messages:
                raw_in_reply_to = msg.get('in_reply_to', '')
                in_reply_to = normalize_message_id(raw_in_reply_to)
                lot = None
                if in_reply_to:
                    comm_result = await session.execute(
                        select(Communication).where(Communication.external_id == in_reply_to)
                    )
                    out_comm = comm_result.scalar_one_or_none()
                    if out_comm:
                        lot = await session.get(LotSupplier, out_comm.lot_supplier_id)

                if not lot:
                    from_field = msg.get('from', '')
                    match = re.search(r'[\w\.-]+@[\w\.-]+', from_field)
                    if not match:
                        continue
                    sender_email = match.group(0).lower()
                    supplier_result = await session.execute(
                        select(Supplier).where(Supplier.email.ilike(sender_email))
                    )
                    supplier = supplier_result.scalar_one_or_none()
                    if not supplier:
                        logger.info('celery.receive_emails.unknown_supplier', email=sender_email)
                        continue
                    lot_result = await session.execute(
                        select(LotSupplier).where(
                            LotSupplier.supplier_id == supplier.id,
                            LotSupplier.status.in_(['CP_REQUESTED', 'PENDING', 'NEGOTIATING'])
                        ).order_by(LotSupplier.created_at.desc()).limit(1)
                    )
                    lot = lot_result.scalar_one_or_none()

                if not lot:
                    continue

                is_cp = bool(msg.get('attachments')) or any(term in (msg.get('subject','') + ' ' + msg.get('body_text','')).lower() for term in ['кп','цена','цены','руб'])
                comm = Communication(
                    lot_supplier_id=lot.id,
                    tender_id=lot.tender_id,
                    direction='incoming',
                    channel='email',
                    subject=msg.get('subject', ''),
                    body_text=msg.get('body_text', ''),
                    message_type='cp_response' if is_cp else 'other',
                    external_id=msg.get('message_id', ''),
                    in_reply_to_external_id=raw_in_reply_to,
                    received_at=datetime.now(timezone.utc),
                )
                session.add(comm)
                await session.flush()

                for att in msg.get('attachments', []):
                    key = f'communications/{str(comm.id)}/{att["filename"]}'
                    success, storage_path = await s3_service.upload_bytes(
                        key=key,
                        content=att['content'],
                        content_type=att['mime_type'],
                    )
                    if success:
                        attachment_record = CommunicationAttachment(
                            communication_id=comm.id,
                            filename=att['filename'],
                            file_size_bytes=len(att['content']),
                            mime_type=att['mime_type'],
                            storage_path=storage_path,
                            is_parsed=False,
                        )
                        session.add(attachment_record)

                if comm.message_type == 'cp_response':
                    offer = CommercialOffer(
                        lot_supplier_id=lot.id,
                        tender_id=lot.tender_id,
                        source_communication_id=comm.id,
                        status='PROCESSING',
                        coverage=0.0,
                        raw_text_snippet=comm.body_text[:2000],
                    )
                    session.add(offer)
                    await session.flush()

                    parse_task = Task(
                        task_type='PARSE_CP',
                        status='PENDING',
                        entity_type='commercial_offer',
                        entity_id=offer.id,
                        progress_percent=0.0,
                        input_data={'cp_id': str(offer.id)}
                    )
                    session.add(parse_task)
                    await session.commit()
                    await session.refresh(parse_task)
                    celery_result = parse_cp_task.delay(str(parse_task.id))
                    parse_task.celery_task_id = celery_result.id
                    await session.commit()

            await session.commit()
    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()
    asyncio.run(_runner())

@celery_app.task
def negotiate_task(task_id: str):
    async def _run():
        await _update_task(task_id, status='IN_PROGRESS', started_at=datetime.now(timezone.utc))
        try:
            async with AsyncSessionLocal() as session:
                task = await _get_task(task_id, session)
                if not task or not task.entity_id:
                    raise ValueError('Task or entity_id not found')
                from app.services.negotiation_service import run_negotiation
                sent_count = await run_negotiation(task.entity_id, session)
            await _update_task(task_id, status='COMPLETED', progress_percent=100.0, completed_at=datetime.now(timezone.utc), result_summary=f'Отправлено уточнений: {sent_count}')
        except Exception as exc:
            logger.error('celery.negotiate_failed', task_id=task_id, error=str(exc))
            await _update_task(task_id, status='FAILED', error_message=str(exc), completed_at=datetime.now(timezone.utc))
    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()
    asyncio.run(_runner())
