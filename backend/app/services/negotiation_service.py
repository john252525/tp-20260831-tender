import structlog
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tender import Tender
from app.models.lot_supplier import LotSupplier
from app.models.supplier import Supplier
from app.models.commercial_offer import CommercialOffer
from app.models.communication import Communication
from app.models.task import Task

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
            comm = Communication(
                lot_supplier_id=lot.id,
                tender_id=tender_id,
                direction='outgoing',
                channel='email',
                subject=f"Уточнение по КП: {tender.title[:80]}",
                body_text="Добрый день!\n\nПросим уточнить следующую информацию:\n" + "\n".join(offer.clarification_items),
                message_type='clarification',
                sent_at=datetime.now(timezone.utc),
            )
            db.add(comm)
            lot.status = 'NEGOTIATING'
            db.add(lot)
            sent_count += 1

    await db.commit()
    logger.info('negotiation_service.completed', tender_id=str(tender_id), sent_count=sent_count)
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
