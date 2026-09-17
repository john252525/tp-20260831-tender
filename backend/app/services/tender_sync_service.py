import asyncio
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.tender_source import TenderSource
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.models.tender_position import TenderPosition
from app.models.tender_requirements import TenderRequirements
from app.services.gosplan_client import GosPlanClient
from app.services.gosplan_positions import extract_purchase_data

logger = structlog.get_logger()

MIME_BY_EXTENSION = {
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.zip': 'application/zip',
    '.rar': 'application/x-rar-compressed',
    '.txt': 'text/plain',
    '.csv': 'text/csv',
}


def _guess_mime(filename: str) -> str:
    """MIME-тип по расширению файла вложения."""
    _, extension = os.path.splitext(filename or '')
    return MIME_BY_EXTENSION.get(extension.lower(), 'application/octet-stream')


def _parse_datetime(value: Any):
    """Безопасно парсит ISO-строку в datetime или возвращает None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        if isinstance(value, str):
            if value.endswith('Z'):
                value = value[:-1] + '+00:00'
            return datetime.fromisoformat(value)
    except Exception:
        return None
    return None


async def enrich_tender_from_purchase(
    tender: Tender,
    purchase_detail: dict,
    db: AsyncSession,
) -> dict:
    """Заполняет тендер позициями, документами, условиями и данными заказчика.

    Данные берутся напрямую из извещения ГосПлан, без скачивания файлов и без LLM.
    Позиции/документы/условия перезаписываются, поэтому функция идемпотентна.
    """
    data = extract_purchase_data(purchase_detail)

    if data['description'] and not tender.description:
        tender.description = data['description']

    customer = data['customer']
    if customer.get('name') and not tender.customer_name:
        tender.customer_name = customer['name'][:500]
    if customer.get('inn') and not tender.customer_inn:
        tender.customer_inn = customer['inn'][:20]
    if customer.get('kpp') and not tender.customer_kpp:
        tender.customer_kpp = customer['kpp'][:20]

    # --- Позиции ---
    await db.execute(delete(TenderPosition).where(TenderPosition.tender_id == tender.id))
    for position in data['positions']:
        db.add(TenderPosition(tender_id=tender.id, **position))

    # --- Документы ---
    await db.execute(delete(TenderDocument).where(TenderDocument.tender_id == tender.id))
    for document in data['documents']:
        filename = (document.get('filename') or 'document')[:500]
        file_size = document.get('file_size')
        db.add(TenderDocument(
            tender_id=tender.id,
            filename=filename,
            file_size_bytes=int(file_size) if file_size else None,
            mime_type=_guess_mime(filename),
            source_url=document['url'],
            parse_status='PENDING',
        ))

    # --- Требования ---
    requirements = data['requirements']
    if requirements:
        await db.execute(delete(TenderRequirements).where(TenderRequirements.tender_id == tender.id))
        db.add(TenderRequirements(
            tender_id=tender.id,
            delivery_date=None,
            delivery_address=requirements.get('delivery_address') or '',
            delivery_conditions=requirements.get('delivery_conditions') or '',
            license_required=requirements.get('license_required', False),
            sro_required=requirements.get('sro_required', False),
            security_bid=requirements.get('security_bid'),
            security_contract=requirements.get('security_contract'),
            prepayment_percent=requirements.get('prepayment_percent'),
            stages_count=requirements.get('stages_count', 1),
            special_conditions=requirements.get('special_conditions') or [],
        ))

    await db.flush()
    logger.info(
        'tender_sync.enriched',
        tender_id=str(tender.id),
        positions=len(data['positions']),
        documents=len(data['documents']),
    )
    return data


def is_source_sync_supported(source: TenderSource) -> bool:
    """Поддерживает ли источник автоматическую синхронизацию.

    Сейчас реально поддержан только API ГосПлан (агрегатор). Ручной ввод и
    источники с произвольным URL опрашивать нельзя: данные из них не приходят,
    а попытки создают шум в статусах источников.
    """
    if source.type != 'aggregator_api':
        return False
    api_url = (source.api_url or '').lower()
    if not api_url.startswith('http'):
        return False
    return 'gosplan.info' in api_url


async def sync_tenders_from_source(source_id: uuid.UUID, db: AsyncSession) -> List[Tender]:
    """Синхронизация тендеров с источником.

    Для источников типа aggregator_api с api_url, содержащим `gosplan.info`,
    используется реальный API ГосПлан с пагинацией: список закупок + детальный
    запрос по каждой (позиции, документы, условия, заказчик).
    Для остальных — временная заглушка.
    """
    source = await db.get(TenderSource, source_id)
    if not source:
        raise ValueError('Источник не найден')

    created_tenders: List[Tender] = []

    try:
        if is_source_sync_supported(source):
            client = GosPlanClient(base_url=source.api_url)

            config = source.config or {}
            page_size = int(config.get('page_size', 50))
            search_query = config.get('search_query')
            skip = 0
            max_pages = int(config.get('max_pages', 1))  # защита от бесконечного цикла
            page_count = 0

            while page_count < max_pages:
                purchases = await client.search_purchases(
                    query=search_query,
                    published_forpast='1y',
                    limit=page_size,
                    skip=skip,
                    sort='published_at_desc',
                )
                if not purchases:
                    break

                for purchase in purchases:
                    purchase_number = purchase.get('purchase_number')
                    if not purchase_number:
                        continue

                    # Дедубликация
                    existing_result = await db.execute(
                        select(Tender).where(
                            Tender.source_id == source.id,
                            Tender.source_tender_id == purchase_number
                        )
                    )
                    if existing_result.scalar_one_or_none():
                        continue

                    nmck = float(purchase.get('max_price')) if purchase.get('max_price') is not None else None
                    published_at = _parse_datetime(purchase.get('published_at'))
                    deadline_at = _parse_datetime(purchase.get('collecting_finished_at'))

                    responsible = purchase.get('responsible', '')
                    customers = purchase.get('customers', [])
                    customer_inn = responsible or (customers[0] if customers else '')

                    title = purchase.get('object_info', '')
                    if not title:
                        title = purchase_number

                    tender = Tender(
                        source_id=source.id,
                        source_tender_id=purchase_number,
                        title=title[:1000],
                        description='',
                        nmck=nmck,
                        published_at=published_at,
                        deadline_at=deadline_at,
                        customer_inn=customer_inn,
                        customer_kpp='',
                        platform='ЕИС',
                        source_url=f"https://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber={purchase_number}",
                        status='NEW'
                    )
                    db.add(tender)
                    await db.flush()  # получить tender.id

                    # Детальная информация: позиции, документы, условия, заказчик.
                    # При сбое (например, 429) пробуем ещё раз после паузы, чтобы
                    # тендер не остался без состава закупки.
                    enrichment_ok = False
                    for enrich_attempt in range(2):
                        try:
                            detail = await client.get_purchase(purchase_number)
                            await enrich_tender_from_purchase(tender, detail, db)
                            enrichment_ok = True
                            break
                        except Exception as exc:
                            logger.warning(
                                'tender_sync.enrich_failed',
                                purchase_number=purchase_number,
                                attempt=enrich_attempt,
                                error=str(exc),
                            )
                            if enrich_attempt == 0:
                                await asyncio.sleep(3)
                    if not enrichment_ok:
                        logger.error('tender_sync.enrich_skipped', purchase_number=purchase_number)

                    created_tenders.append(tender)

                skip += page_size
                page_count += 1
                if len(purchases) < page_size:
                    break  # последняя страница
        else:
            # Источник не поддерживается: раньше здесь создавались фиктивные
            # тендеры, из-за чего база засорялась мусорными записями при
            # каждой автосинхронизации. Теперь синхронизация не выполняется.
            message = (
                f'Источник "{source.name}" (тип {source.type}, url {source.api_url}) '
                'не поддерживается автоматической синхронизацией'
            )
            logger.error('tender_sync.unsupported_source', source_id=str(source_id), source_type=source.type)
            source.last_sync_status = 'error'
            source.last_error = message
            source.last_sync_at = datetime.now(timezone.utc)
            await db.commit()
            return []

        source.last_sync_at = datetime.now(timezone.utc)
        source.last_sync_status = 'success'
        source.last_error = None
        await db.commit()
        logger.info('tender_sync.completed', source_id=str(source_id), count=len(created_tenders))
        return created_tenders

    except Exception as exc:
        logger.error('tender_sync.failed', source_id=str(source_id), error=str(exc))
        source.last_sync_status = 'error'
        source.last_error = str(exc)
        source.last_sync_at = datetime.now(timezone.utc)
        await db.commit()
        raise
