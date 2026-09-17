import asyncio
import re
from datetime import datetime, timezone, timedelta
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

# Через сколько минут задача в PENDING считается зависшей
STUCK_TASK_MINUTES = 15

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

                # Статус тендера выводится из состояния лотов
                try:
                    from app.services.tender_status_service import recalculate_tender_status
                    await recalculate_tender_status(tender_id, session)
                except Exception as exc:
                    logger.warning('celery.status_recalc_failed', task_id=task_id, error=str(exc))

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

                    # Письмо-ответ уже получено: статус тендера пересчитываем
                    # сразу, не дожидаясь разбора КП.
                    try:
                        from app.services.tender_status_service import recalculate_tender_status
                        await recalculate_tender_status(lot.tender_id, session)
                    except Exception as exc:
                        logger.warning('celery.status_recalc_failed', error=str(exc))

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

@celery_app.task
def sync_active_sources_task():
    """Периодически синхронизирует активные источники тендеров.

    Интервал опроса берётся из настроек источника (poll_interval_minutes):
    если с прошлой синхронизации прошло меньше времени, источник пропускается.
    """
    async def _run():
        from app.models.tender_source import TenderSource
        from app.models.setting import Setting

        async with AsyncSessionLocal() as session:
            # Значение по умолчанию для интервала опроса
            default_interval = 30
            setting_result = await session.execute(
                select(Setting).where(Setting.section == 'tender_source', Setting.key == 'poll_interval_minutes')
            )
            setting = setting_result.scalar_one_or_none()
            if setting is not None:
                try:
                    default_interval = int(setting.value)
                except (TypeError, ValueError):
                    default_interval = 30

            from app.services.tender_sync_service import is_source_sync_supported

            candidates = (await session.execute(
                select(TenderSource).where(TenderSource.is_active == True)
            )).scalars().all()
            # Опрашиваем только источники, для которых синхронизация реально
            # реализована: иначе автосинхронизация крутится впустую.
            sources = [s for s in candidates if is_source_sync_supported(s)]

            now = datetime.now(timezone.utc)
            started = 0
            for source in sources:
                interval = default_interval
                config = source.config or {}
                if config.get('poll_interval_minutes'):
                    try:
                        interval = int(config['poll_interval_minutes'])
                    except (TypeError, ValueError):
                        pass
                if source.last_sync_at is not None:
                    elapsed_minutes = (now - source.last_sync_at).total_seconds() / 60
                    if elapsed_minutes < interval:
                        continue

                task = Task(
                    task_type='SYNC_TENDERS',
                    status='PENDING',
                    entity_type='tender_source',
                    entity_id=source.id,
                    progress_percent=0.0,
                    input_data={'source_id': str(source.id), 'trigger': 'schedule'},
                )
                session.add(task)
                await session.flush()
                celery_result = sync_tenders_task.delay(str(task.id))
                task.celery_task_id = celery_result.id
                started += 1

            await session.commit()
            logger.info('celery.sync_active_sources_done', candidates=len(candidates), pollable=len(sources), started=started)

    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()

    asyncio.run(_runner())


@celery_app.task
def process_new_tenders_task():
    """Автоматически ставит на обработку новые тендеры.

    Обрабатываются тендеры со статусом NEW, по которым ещё нет активной задачи
    PROCESS_TENDER. Это замыкает конвейер: импорт -> обработка -> оценка.
    """
    async def _run():
        from app.models.tender_status_history import TenderStatusHistory  # noqa: F401

        async with AsyncSessionLocal() as session:
            active_result = await session.execute(
                select(Task.entity_id).where(
                    Task.task_type == 'PROCESS_TENDER',
                    Task.status.in_(['PENDING', 'IN_PROGRESS']),
                )
            )
            busy_ids = {row[0] for row in active_result.all() if row[0] is not None}

            tenders = (await session.execute(
                select(Tender).where(Tender.status == 'NEW').order_by(Tender.created_at).limit(50)
            )).scalars().all()

            started = 0
            for tender in tenders:
                if tender.id in busy_ids:
                    continue
                task = Task(
                    task_type='PROCESS_TENDER',
                    status='PENDING',
                    entity_type='tender',
                    entity_id=tender.id,
                    progress_percent=0.0,
                    input_data={'tender_id': str(tender.id), 'trigger': 'schedule'},
                )
                session.add(task)
                await session.flush()
                celery_result = process_tender_task.delay(str(task.id))
                task.celery_task_id = celery_result.id
                started += 1

            await session.commit()
            logger.info('celery.process_new_tenders_done', candidates=len(tenders), started=started)

    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()

    asyncio.run(_runner())


@celery_app.task
def start_pipeline_for_scored_tenders_task():
    """Запускает полный конвейер для оценённых тендеров.

    После скоринга конвейер останавливался: генерация запросов, поиск
    поставщиков, сбор email и черновики писем запускались только вручную
    через API. Здесь лучшие по скору тендеры уходят в конвейер автоматически.
    """
    async def _run():
        from app.models.setting import Setting

        async with AsyncSessionLocal() as session:
            # Порог скора из настроек: в конвейер уходят только лучшие
            min_score = 60.0
            setting_result = await session.execute(
                select(Setting).where(Setting.section == 'scoring', Setting.key == 'min_total_score')
            )
            setting = setting_result.scalar_one_or_none()
            if setting is not None:
                try:
                    min_score = float(setting.value)
                except (TypeError, ValueError):
                    pass

            # Не запускаем повторно то, что уже в работе
            active_result = await session.execute(
                select(Task.entity_id).where(
                    Task.task_type.in_(['PIPELINE', 'SEARCH_SUPPLIERS']),
                    Task.status.in_(['PENDING', 'IN_PROGRESS']),
                )
            )
            busy_ids = {row[0] for row in active_result.all() if row[0] is not None}

            candidates = (await session.execute(
                select(Tender)
                .where(Tender.status == 'SCORED', Tender.score >= min_score)
                .order_by(Tender.score.desc())
                .limit(5)
            )).scalars().all()

            started = 0
            for tender in candidates:
                if tender.id in busy_ids:
                    continue
                task = Task(
                    task_type='PIPELINE',
                    status='PENDING',
                    entity_type='tender',
                    entity_id=tender.id,
                    progress_percent=0.0,
                    input_data={'tender_id': str(tender.id), 'trigger': 'schedule'},
                )
                session.add(task)
                await session.flush()
                celery_result = run_full_pipeline_task.delay(str(task.id))
                task.celery_task_id = celery_result.id
                started += 1

            await session.commit()
            logger.info('celery.start_pipeline_done', candidates=len(candidates), started=started, min_score=min_score)

    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()

    asyncio.run(_runner())


@celery_app.task
def request_discounts_task():
    """Запрашивает улучшение цен у поставщиков с завышенными КП.

    Сравнивает предложения по лотам и просит поставщиков пересмотреть цены,
    если разрыв превышает ``price_diff_threshold_percent``.
    """
    async def _run():
        from app.services.negotiation_service import request_discounts

        async with AsyncSessionLocal() as session:
            tender_ids = [row[0] for row in (await session.execute(
                select(LotSupplier.tender_id)
                .where(LotSupplier.status.in_(('CP_RECEIVED', 'NEGOTIATING')))
                .group_by(LotSupplier.tender_id)
                .limit(50)
            )).all()]

            total = 0
            for tender_id in tender_ids:
                try:
                    total += await request_discounts(str(tender_id), session)
                except Exception as exc:
                    logger.warning('celery.discount_failed', tender_id=str(tender_id), error=str(exc))

            logger.info('celery.request_discounts_done', tenders=len(tender_ids), sent=total)

    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()

    asyncio.run(_runner())


@celery_app.task
def send_reminders_task():
    """Напоминает поставщикам, не ответившим на запрос КП.

    Раньше напоминания не отправлялись вообще: настройка
    ``reminder_after_hours`` в БД не использовалась, и лоты навсегда
    оставались в CP_REQUESTED.
    """
    async def _run():
        from app.services.negotiation_service import send_reminders

        async with AsyncSessionLocal() as session:
            tender_ids = [row[0] for row in (await session.execute(
                select(LotSupplier.tender_id)
                .where(LotSupplier.status == 'CP_REQUESTED')
                .group_by(LotSupplier.tender_id)
                .limit(50)
            )).all()]

            total = 0
            for tender_id in tender_ids:
                try:
                    total += await send_reminders(str(tender_id), session)
                except Exception as exc:
                    logger.warning('celery.reminder_failed', tender_id=str(tender_id), error=str(exc))

            logger.info('celery.send_reminders_done', tenders=len(tender_ids), sent=total)

    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()

    asyncio.run(_runner())


@celery_app.task
def reprocess_unenriched_tenders_task():
    """Повторно обрабатывает тендеры, упавшие из-за отсутствия данных.

    Тендеры, импортированные до появления разбора состава закупки, уходили
    в ERROR с сообщением «Нет текста для семантического анализа». Теперь
    обработка умеет добирать позиции из API ГосПлан, поэтому такие тендеры
    имеет смысл вернуть в работу.
    """
    async def _run():
        async with AsyncSessionLocal() as session:
            broken = (await session.execute(
                select(Tender).where(
                    Tender.status == 'ERROR',
                    Tender.processing_error == 'Нет текста для семантического анализа',
                ).order_by(Tender.created_at).limit(20)
            )).scalars().all()

            started = 0
            for tender in broken:
                task = Task(
                    task_type='PROCESS_TENDER',
                    status='PENDING',
                    entity_type='tender',
                    entity_id=tender.id,
                    progress_percent=0.0,
                    input_data={'tender_id': str(tender.id), 'trigger': 'reprocess_unenriched'},
                )
                session.add(task)
                await session.flush()
                celery_result = process_tender_task.delay(str(task.id))
                task.celery_task_id = celery_result.id
                started += 1

            await session.commit()
            logger.info('celery.reprocess_unenriched_done', candidates=len(broken), started=started)

    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()

    asyncio.run(_runner())


@celery_app.task
def requeue_stuck_tasks_task():
    """Перезапускает задачи, зависшие в PENDING без задания в очереди.

    Такие задачи появляются, если воркер был остановлен между созданием записи
    Task и постановкой задания в Celery: запись в БД есть, а в Redis — нет.
    """
    async def _run():
        # Задача считается зависшей, если она в PENDING дольше порога.
        # Проверять состояние через Celery AsyncResult нельзя: для неизвестного
        # (потерянного) задания Celery возвращает PENDING, и такая задача
        # никогда бы не была перезапущена.
        stuck_before = datetime.now(timezone.utc) - timedelta(minutes=STUCK_TASK_MINUTES)

        async with AsyncSessionLocal() as session:
            stuck = (await session.execute(
                select(Task).where(
                    Task.status == 'PENDING',
                    Task.created_at < stuck_before,
                ).order_by(Task.created_at).limit(100)
            )).scalars().all()

            requeued = 0
            for task in stuck:
                runner = TASK_RUNNERS.get(task.task_type)
                if runner is None:
                    continue
                try:
                    celery_result = runner(str(task.id))
                    task.celery_task_id = celery_result.id
                    task.error_message = None
                    requeued += 1
                except Exception as exc:
                    logger.warning('celery.requeue_failed', task_id=str(task.id), error=str(exc))

            await session.commit()
            logger.info('celery.requeue_stuck_done', stuck=len(stuck), requeued=requeued)

    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()

    asyncio.run(_runner())


# Соответствие типа задачи и Celery-задания для повторного запуска
TASK_RUNNERS = {
    'PROCESS_TENDER': lambda task_id: process_tender_task.delay(task_id),
    'SYNC_TENDERS': lambda task_id: sync_tenders_task.delay(task_id),
    'SEARCH_SUPPLIERS': lambda task_id: search_suppliers_task.delay(task_id),
    'PARSE_CP': lambda task_id: parse_cp_task.delay(task_id),
    'SEND_COMMUNICATIONS': lambda task_id: send_communications_task.delay(task_id),
    'NEGOTIATE': lambda task_id: negotiate_task.delay(task_id),
    'SEND_REMINDERS': lambda task_id: send_reminders_task.delay(task_id),
    'REQUEST_DISCOUNTS': lambda task_id: request_discounts_task.delay(task_id),
    'PIPELINE': lambda task_id: run_full_pipeline_task.delay(task_id),
}


@celery_app.task
def run_full_pipeline_task(task_id: str):
    """Полный конвейер: обработка тендера, генерация запросов, поиск поставщиков, краулинг, черновики."""

    async def _run():
        await _update_task(task_id, status='IN_PROGRESS', started_at=datetime.now(timezone.utc))
        try:
            async with AsyncSessionLocal() as session:
                task = await _get_task(task_id, session)
                if not task or not task.entity_id:
                    raise ValueError('Task or entity_id not found')
                tender_id = task.entity_id
                from app.services.pipeline_service import run_full_pipeline_for_tender
                result = await run_full_pipeline_for_tender(tender_id, session, task_id=task_id)
            # Задача уже завершена внутри pipeline_service.complete_pipeline_task
        except Exception as exc:
            logger.error('celery.run_full_pipeline_failed', task_id=task_id, error=str(exc))
            await _update_task(task_id, status='FAILED', error_message=str(exc),
                               completed_at=datetime.now(timezone.utc))

    async def _runner():
        try:
            await _run()
        finally:
            await engine.dispose()

    asyncio.run(_runner())
