import structlog
from datetime import datetime, timezone
from typing import Dict
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tender import Tender
from app.models.lot_supplier import LotSupplier
from app.models.supplier import Supplier
from app.models.commercial_offer import CommercialOffer
from app.models.communication import Communication
from app.models.task import Task
from app.services.email_service import send_email
from app.services.template_rendering import render_template, build_cp_context

logger = structlog.get_logger()

async def run_negotiation(tender_id: str, db: AsyncSession) -> int:
    """Базовая реализация переговоров: для КП с недостающими данными создаёт запрос уточнений."""
    tender = await db.get(Tender, tender_id)
    if not tender:
        return 0

    lots = (await db.execute(
        select(LotSupplier).where(LotSupplier.tender_id == tender_id)
    )).scalars().all()

    sent_count = 0
    for lot in lots:
        supplier = await db.get(Supplier, lot.supplier_id)
        if not supplier or not supplier.email:
            continue

        offers = (await db.execute(
            select(CommercialOffer).where(
                CommercialOffer.lot_supplier_id == lot.id,
                CommercialOffer.clarification_needed == True
            )
        )).scalars().all()

        for offer in offers:
            if not offer.clarification_items:
                continue

            clarification_items = "\n".join(f"- {item}" for item in offer.clarification_items)
            subject = f"Уточнение по КП: {tender.title[:80]}"
            body_text = (
                "Добрый день!\n\n"
                "Благодарим за коммерческое предложение. "
                "Просим уточнить следующую информацию:\n"
                f"{clarification_items}"
            )

            # Шаблон уточнения из настроек, если он задан
            try:
                from app.services.settings_service import get_section_settings
                templates = await get_section_settings(db, 'templates') or {}
                clarification_template = templates.get('clarification') or {}
                context = {
                    'clarification_items': clarification_items,
                    'lot_name': tender.title,
                    'company_signature': '',
                }
                if clarification_template.get('subject'):
                    subject = await render_template(clarification_template['subject'], context)
                if clarification_template.get('body'):
                    body_text = await render_template(clarification_template['body'], context)
            except Exception as exc:
                logger.warning('negotiation_service.template_failed', error=str(exc))

            # Письмо должно быть реально отправлено, иначе фиксировать
            # коммуникацию нельзя: поставщик ничего не увидит.
            sent, message_id = await send_email(
                to_address=supplier.email,
                subject=subject,
                body_text=body_text,
                db=db,
            )
            if not sent:
                logger.warning('negotiation_service.email_not_sent',
                               supplier_id=str(supplier.id), email=supplier.email)
                continue

            comm = Communication(
                lot_supplier_id=lot.id,
                tender_id=tender_id,
                direction='outgoing',
                channel='email',
                subject=subject,
                body_text=body_text,
                message_type='clarification',
                external_id=message_id,
                sent_at=datetime.now(timezone.utc),
            )
            db.add(comm)
            lot.status = 'NEGOTIATING'
            db.add(lot)
            sent_count += 1

    await db.flush()

    # Переговоры могли закрыть лоты — пересчитываем статус тендера.
    try:
        from app.services.tender_status_service import recalculate_tender_status
        await recalculate_tender_status(tender.id, db)
    except Exception as exc:
        logger.warning('negotiation_service.status_recalc_failed', tender_id=str(tender_id), error=str(exc))

    await db.commit()
    logger.info('negotiation_service.completed', tender_id=str(tender_id), sent_count=sent_count)
    return sent_count

async def send_reminders(tender_id: str, db: AsyncSession) -> int:
    """Напоминает поставщикам, которые не ответили на запрос КП.

    Через ``reminder_after_hours`` после отправки запроса и до истечения
    ``response_timeout_hours`` отправляется одно напоминание.
    """
    from datetime import timedelta
    from app.models.setting import Setting
    from app.services.settings_service import get_section_settings

    tender = await db.get(Tender, tender_id)
    if not tender:
        return 0

    comm_settings = await get_section_settings(db, 'communication') or {}
    try:
        reminder_after = float(comm_settings.get('reminder_after_hours', 24))
    except (TypeError, ValueError):
        reminder_after = 24.0
    try:
        response_timeout = float(comm_settings.get('response_timeout_hours', 48))
    except (TypeError, ValueError):
        response_timeout = 48.0

    now = datetime.now(timezone.utc)
    sent_count = 0
    dry_run = bool((await get_section_settings(db, 'communication') or {}).get('reminders_dry_run', False))

    lots = (await db.execute(
        select(LotSupplier).where(
            LotSupplier.tender_id == tender_id,
            LotSupplier.status.in_(('CP_REQUESTED', 'NO_RESPONSE')),
        )
    )).scalars().all()

    for lot in lots:
        supplier = await db.get(Supplier, lot.supplier_id)
        if not supplier or not supplier.email:
            continue

        # Когда отправляли запрос КП
        request_comm = (await db.execute(
            select(Communication).where(
                Communication.lot_supplier_id == lot.id,
                Communication.message_type == 'cp_request',
            ).order_by(Communication.created_at.desc()).limit(1)
        )).scalar_one_or_none()
        if request_comm is None or request_comm.sent_at is None:
            continue

        elapsed_hours = (now - request_comm.sent_at).total_seconds() / 3600
        if elapsed_hours < reminder_after:
            continue

        # Ответ не пришёл дольше допустимого срока: помечаем лот, но напоминание
        # всё равно отправляем — иначе такие лоты остаются без движения навсегда.
        if elapsed_hours > response_timeout and lot.status == 'CP_REQUESTED':
            lot.status = 'NO_RESPONSE'
            db.add(lot)

        # Напоминание отправляется один раз
        already = (await db.execute(
            select(Communication).where(
                Communication.lot_supplier_id == lot.id,
                Communication.message_type == 'reminder',
            ).limit(1)
        )).scalar_one_or_none()
        if already is not None:
            continue

        # На отвеченные лоты напоминания не шлём
        if lot.status not in ('CP_REQUESTED', 'NO_RESPONSE'):
            continue

        subject = f'Напоминание: запрос КП {tender.title[:80]}'
        body_text = (
            'Добрый день!\n\n'
            'Напоминаем о ранее направленном запросе коммерческого предложения. '
            'Будем признательны за оперативный ответ.'
        )
        try:
            templates = await get_section_settings(db, 'templates') or {}
            reminder_template = templates.get('cp_reminder') or {}
            context = {'lot_name': tender.title, 'company_signature': ''}
            if reminder_template.get('subject'):
                subject = await render_template(reminder_template['subject'], context)
            if reminder_template.get('body'):
                body_text = await render_template(reminder_template['body'], context)
        except Exception as exc:
            logger.warning('negotiation_service.reminder_template_failed', error=str(exc))

        if dry_run:
            logger.info('negotiation_service.reminder_dry_run', email=supplier.email, elapsed_hours=round(elapsed_hours, 1))
            sent_count += 1
            continue

        sent, message_id = await send_email(
            to_address=supplier.email,
            subject=subject,
            body_text=body_text,
            db=db,
        )
        if not sent:
            logger.warning('negotiation_service.reminder_not_sent', email=supplier.email)
            continue

        db.add(Communication(
            lot_supplier_id=lot.id,
            tender_id=tender_id,
            direction='outgoing',
            channel='email',
            subject=subject,
            body_text=body_text,
            message_type='reminder',
            external_id=message_id,
            sent_at=now,
        ))
        sent_count += 1

    await db.commit()
    logger.info('negotiation_service.reminders_done', tender_id=str(tender_id), sent=sent_count)
    return sent_count


async def request_discounts(tender_id: str, db: AsyncSession) -> int:
    """Запрашивает улучшение цен у поставщиков по итогам сравнения КП.

    Торг ведётся только там, где это обосновано: у поставщиков, чья цена
    заметно выше лучшего предложения (``price_diff_threshold_percent``),
    и не чаще ``max_discount_requests_per_supplier`` раз на лот.
    """
    from app.services.settings_service import get_section_settings
    from app.models.setting import Setting

    tender = await db.get(Tender, tender_id)
    if not tender:
        return 0

    comm_settings = await get_section_settings(db, 'communication') or {}
    try:
        price_threshold = float(comm_settings.get('price_diff_threshold_percent', 5.0))
    except (TypeError, ValueError):
        price_threshold = 5.0
    try:
        max_requests = int(comm_settings.get('max_discount_requests_per_supplier', 2))
    except (TypeError, ValueError):
        max_requests = 2

    lots = (await db.execute(
        select(LotSupplier).where(LotSupplier.tender_id == tender_id)
    )).scalars().all()
    if len(lots) < 2:
        return 0

    # Лучшее предложение по каждому лоту определяем по общей стоимости
    offers_by_lot: Dict[str, CommercialOffer] = {}
    for lot in lots:
        offer = (await db.execute(
            select(CommercialOffer).where(
                CommercialOffer.lot_supplier_id == lot.id,
                CommercialOffer.status == 'FULL',
                CommercialOffer.total_cost_with_all.is_not(None),
            ).order_by(CommercialOffer.total_cost_with_all.asc()).limit(1)
        )).scalar_one_or_none()
        if offer is not None:
            offers_by_lot[str(lot.id)] = offer

    if not offers_by_lot:
        return 0

    best_cost = min(float(o.total_cost_with_all) for o in offers_by_lot.values())
    if best_cost <= 0:
        return 0

    context = await build_cp_context(tender, db)
    templates = await get_section_settings(db, 'templates') or {}
    discount_template = templates.get('discount_request') or {}

    sent_count = 0
    for lot in lots:
        offer = offers_by_lot.get(str(lot.id))
        if offer is None:
            continue

        # Сначала проверяем экономическую целесообразность торга,
        # и только потом обращаемся к поставщику.
        price_gap = (float(offer.total_cost_with_all) - best_cost) / best_cost * 100
        if price_gap < price_threshold:
            continue

        supplier = await db.get(Supplier, lot.supplier_id)
        if not supplier or not supplier.email:
            continue

        # Ограничение числа запросов на поставщика
        already_count = (await db.execute(
            select(func.count(Communication.id)).where(
                Communication.lot_supplier_id == lot.id,
                Communication.message_type == 'discount_request',
            )
        )).scalar_one()
        if already_count >= max_requests:
            continue

        discount_positions = (
            f"- Текущая цена: {float(offer.total_cost_with_all):,.2f} руб.\n"
            f"- Лучшее предложение по закупке: {best_cost:,.2f} руб.\n"
            f"- Разница: {price_gap:.1f}%"
        )

        subject = f'Запрос улучшения условий: {tender.title[:80]}'
        body_text = (
            'Добрый день!\n\n'
            'Благодарим за коммерческое предложение. '
            'В настоящий момент мы рассматриваем несколько предложений. '
            'Будем признательны, если вы сможете пересмотреть цены.\n\n'
            f'{discount_positions}'
        )
        render_context = dict(context)
        render_context['discount_positions'] = discount_positions
        render_context['lot_name'] = tender.title
        try:
            if discount_template.get('subject'):
                subject = await render_template(discount_template['subject'], render_context)
            if discount_template.get('body'):
                body_text = await render_template(discount_template['body'], render_context)
        except Exception as exc:
            logger.warning('negotiation_service.discount_template_failed', error=str(exc))

        sent, message_id = await send_email(
            to_address=supplier.email,
            subject=subject,
            body_text=body_text,
            db=db,
        )
        if not sent:
            logger.warning('negotiation_service.discount_not_sent', email=supplier.email)
            continue

        db.add(Communication(
            lot_supplier_id=lot.id,
            tender_id=tender_id,
            direction='outgoing',
            channel='email',
            subject=subject,
            body_text=body_text,
            message_type='discount_request',
            external_id=message_id,
            sent_at=datetime.now(timezone.utc),
        ))
        lot.status = 'NEGOTIATING'
        db.add(lot)
        sent_count += 1

    await db.flush()
    try:
        from app.services.tender_status_service import recalculate_tender_status
        await recalculate_tender_status(tender.id, db)
    except Exception as exc:
        logger.warning('negotiation_service.status_recalc_failed', tender_id=str(tender_id), error=str(exc))

    await db.commit()
    logger.info('negotiation_service.discounts_done', tender_id=str(tender_id), sent=sent_count)
    return sent_count


async def get_negotiation_status(tender_id: UUID, db: AsyncSession) -> dict:
    """Возвращает реальный статус переговоров по тендеру.
    Собирает данные о задачах NEGOTIATE и предложениях поставщиков.
    """
    # Находим последнюю задачу NEGOTIATE
    task_result = await db.execute(
        select(Task).where(
            Task.entity_type == 'tender',
            Task.entity_id == tender_id,
            Task.task_type == 'NEGOTIATE'
        ).order_by(Task.created_at.desc()).limit(1)
    )
    task = task_result.scalar_one_or_none()

    # Общее количество завершённых/запущенных задач переговоров = оценка циклов
    cycles_completed_result = await db.execute(
        select(func.count(Task.id)).where(
            Task.entity_type == 'tender',
            Task.entity_id == tender_id,
            Task.task_type == 'NEGOTIATE',
            Task.status == 'COMPLETED'
        )
    )
    cycles_completed = cycles_completed_result.scalar_one()

    started_at = task.started_at or task.created_at if task else None

    # Определяем общий статус
    if task is None:
        overall_status = 'IN_PROGRESS'  # переговоры ещё не начинали, но по ТЗ допустимый статус
    elif task.status == 'PENDING' or task.status == 'IN_PROGRESS':
        overall_status = 'IN_PROGRESS'
    elif task.status == 'FAILED':
        overall_status = 'FAILED'
    else:
        overall_status = 'COMPLETED'

    # Получаем лоты и их КП
    lots = (await db.execute(
        select(LotSupplier).where(LotSupplier.tender_id == tender_id)
    )).scalars().all()

    suppliers = []
    for lot in lots:
        supplier = await db.get(Supplier, lot.supplier_id)
        if not supplier:
            continue

        # Получаем все КП для лота, отсортированные по дате создания (первое и последнее)
        offers_result = await db.execute(
            select(CommercialOffer).where(
                CommercialOffer.lot_supplier_id == lot.id
            ).order_by(CommercialOffer.created_at.asc())
        )
        offers = offers_result.scalars().all()

        initial_margin = None
        current_margin = None
        improvement = None

        if offers:
            first_offer = offers[0]
            last_offer = offers[-1]
            initial_margin = first_offer.margin_percent
            current_margin = last_offer.margin_percent
            if initial_margin is not None and current_margin is not None:
                improvement = current_margin - initial_margin

        # Определяем последнее действие по сообщениям лота
        last_action = None
        last_action_at = None
        comm_result = await db.execute(
            select(Communication).where(
                Communication.lot_supplier_id == lot.id
            ).order_by(Communication.created_at.desc()).limit(1)
        )
        last_comm = comm_result.scalar_one_or_none()
        if last_comm:
            last_action = last_comm.message_type
            last_action_at = last_comm.sent_at or last_comm.received_at

        suppliers.append({
            'supplier_id': str(supplier.id),
            'supplier_name': supplier.name,
            'initial_margin_percent': initial_margin,
            'current_margin_percent': current_margin,
            'improvement_percent': improvement,
            'status': lot.status,
            'last_action': last_action,
            'last_action_at': last_action_at.isoformat() if last_action_at else None,
        })

    return {
        'status': overall_status,
        'cycles_completed': cycles_completed,
        'max_cycles': 2,
        'started_at': started_at.isoformat() if started_at else None,
        'suppliers': suppliers
    }
