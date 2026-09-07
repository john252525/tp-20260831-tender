import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.tender_source import TenderSource
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.services.gosplan_client import GosPlanClient

logger = structlog.get_logger()

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

async def sync_tenders_from_source(source_id: uuid.UUID, db: AsyncSession) -> List[Tender]:
    """Синхронизация тендеров с источником.

    Для источников типа aggregator_api с api_url, содержащим `gosplan.info`,
    используется реальный API ГосПлан с пагинацией. Для остальных — временная заглушка.
    """
    source = await db.get(TenderSource, source_id)
    if not source:
        raise ValueError('Источник не найден')

    created_tenders: List[Tender] = []

    try:
        if source.type == 'aggregator_api' and 'gosplan.info' in source.api_url:
            client = GosPlanClient(base_url=source.api_url)

            config = source.config or {}
            page_size = int(config.get('page_size', 50))
            search_query = config.get('search_query')
            skip = 0
            max_pages = int(config.get('max_pages', 10))  # защита от бесконечного цикла
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
                        description='',  # TODO: заполнять из полной информации о закупке
                        nmck=nmck,
                        published_at=published_at,
                        deadline_at=deadline_at,
                        customer_inn=customer_inn,
                        customer_kpp='',  # TODO: брать из API организаций
                        platform='ЕИС',
                        source_url=f"https://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber={purchase_number}",
                        status='NEW'
                    )
                    db.add(tender)
                    await db.flush()  # получить tender.id

                    # Загрузка документов
                    docs = await client.get_purchase_documents(purchase_number)
                    for doc in docs:
                        doc_url = doc.get('url') or doc.get('link') or ''
                        if not doc_url:
                            continue
                        filename = doc.get('filename') or doc.get('name') or doc_url.split('/')[-1]
                        tender_doc = TenderDocument(
                            tender_id=tender.id,
                            filename=filename,
                            mime_type=doc.get('mime_type', 'application/octet-stream'),
                            source_url=doc_url,
                            parse_status='PENDING',
                        )
                        db.add(tender_doc)

                    created_tenders.append(tender)

                skip += page_size
                page_count += 1
                if len(purchases) < page_size:
                    break  # последняя страница
        else:
            # Временная заглушка для источников, не являющихся ГосПлан
            logger.warning('tender_sync.stub_used', source_id=str(source_id))
            for i in range(10):
                stub_id = f'stub-{uuid.uuid4().hex[:12]}'
                tender = Tender(
                    source_id=source.id,
                    source_tender_id=stub_id,
                    title=f'Тестовый тендер {i}',
                    description='Описание тестового тендера',
                    nmck=1000000.0,
                    status='NEW'
                )
                db.add(tender)
                created_tenders.append(tender)

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
