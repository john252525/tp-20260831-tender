import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional
import structlog
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.models.tender_position import TenderPosition
from app.models.tender_requirements import TenderRequirements
from app.models.tender_status_history import TenderStatusHistory
from app.models.category import Category
from app.services.document_parser import extract_text
from app.services.embedding_service import generate_embedding, cosine_similarity
from app.services.llm_service import extract_structured_data
from app.services.scoring_service import calculate_score
from app.services.s3_service import s3_service

logger = structlog.get_logger()

async def process_tender(tender_id: uuid.UUID, db: AsyncSession):
    """Обрабатывает тендер: загрузка документов, парсинг, семантический фильтр, извлечение структуры, скоринг.
    При ошибке переводит тендер в ERROR."""
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise ValueError('Тендер не найден')

    # Решение человека неприкосновенно: одобренный или отклонённый тендер
    # не должен переобрабатываться автоматикой и терять свой статус.
    if tender.status in ('APPROVED', 'REJECTED'):
        logger.info('tender_processor.skipped_manual_decision',
                    tender_id=str(tender_id), status=tender.status)
        return

    previous_status = tender.status
    tender.status = 'PROCESSING'
    history = TenderStatusHistory(
        tender_id=tender.id,
        status='PROCESSING',
        previous_status=previous_status,
        note='Начало обработки тендера'
    )
    db.add(history)
    await db.flush()

    # Ошибка относится к предыдущему прогону — сбрасываем её в начале нового,
    # иначе успешно обработанный тендер останется с устаревшим сообщением.
    tender.processing_error = None

    try:
        # Тендеры, импортированные до появления разбора состава закупки, могут
        # не иметь ни позиций, ни описания. Перед обработкой пробуем добрать
        # данные из API ГосПлан, иначе тендер уйдёт в ERROR без причины.
        await _ensure_tender_enriched(tender, db)

        documents = await _load_documents(tender_id, db)
        if not documents:
            logger.warning('tender_processor.no_documents', tender_id=str(tender_id))

        all_text = ''
        for doc in documents:
            if doc.parse_status in ('PENDING', 'ERROR'):
                text = await _parse_document(doc)
                all_text += text + '\n'
                doc.parsed_text = text
                # SKIPPED — файл недоступен (например, zakupki.gov.ru закрыт с хоста).
                # Повторно качать не будем, чтобы не блокировать обработку.
                doc.parse_status = 'PARSED' if text else 'SKIPPED'
                db.add(doc)
        await db.commit()

        # Семантический портрет: тексты документов, а если их нет и описание
        # пустое — позиции, уже полученные из API ГосПлан.
        semantic_text = all_text
        if not semantic_text and not tender.description:
            semantic_text = await _positions_text(tender_id, db)

        await _semantic_filter(tender, semantic_text, db)

        if tender.status == 'RELEVANT':
            # Позиции из API ГосПлан приоритетнее: LLM-извлечение запускаем
            # только если состава закупки ещё нет.
            has_positions = (await db.execute(
                select(func.count(TenderPosition.id)).where(TenderPosition.tender_id == tender_id)
            )).scalar_one() > 0
            if not has_positions:
                await _extract_tender_structure(tender, all_text, db)
            scoring_history = TenderStatusHistory(
                tender_id=tender.id,
                status='SCORING',
                previous_status='RELEVANT',
                note='Расчёт скора'
            )
            db.add(scoring_history)
            await db.flush()

            try:
                score, components = await calculate_score(tender, db)
                tender.score = score
                tender.score_components = components
                tender.status = 'SCORED'
                score_history = TenderStatusHistory(
                    tender_id=tender.id,
                    status='SCORED',
                    previous_status='SCORING',
                    note=f'Скор: {score:.2f}'
                )
                db.add(score_history)
            except Exception as score_exc:
                logger.error('tender_processor.scoring_failed', tender_id=str(tender_id), error=str(score_exc))
                tender.status = 'ERROR'
                tender.processing_error = 'Ошибка скоринга'
                error_history = TenderStatusHistory(
                    tender_id=tender.id,
                    status='ERROR',
                    previous_status='SCORING',
                    note='Ошибка скоринга'
                )
                db.add(error_history)
                await db.commit()
                raise

        await db.commit()
        logger.info('tender_processor.completed', tender_id=str(tender_id), status=tender.status)
    except Exception as exc:
        logger.error('tender_processor.error', tender_id=str(tender_id), error=str(exc))
        if tender.status != 'ERROR':
            tender.status = 'ERROR'
            tender.processing_error = str(exc)
            error_history = TenderStatusHistory(
                tender_id=tender.id,
                status='ERROR',
                previous_status=tender.status if tender.status != 'ERROR' else None,
                note='Ошибка обработки тендера'
            )
            db.add(error_history)
        await db.commit()
        raise

async def _ensure_tender_enriched(tender: Tender, db: AsyncSession) -> bool:
    """Добирает состав закупки из API ГосПлан, если данных ещё нет.

    Нужно для тендеров, импортированных до появления разбора позиций:
    без этого они навсегда остаются без описания и уходят в ERROR.
    """
    from app.models.tender_source import TenderSource
    from app.services.tender_sync_service import enrich_tender_from_purchase, is_source_sync_supported
    from app.services.gosplan_client import GosPlanClient

    has_positions = (await db.execute(
        select(func.count(TenderPosition.id)).where(TenderPosition.tender_id == tender.id)
    )).scalar_one() > 0
    if has_positions or (tender.description or '').strip():
        return False

    if not tender.source_tender_id:
        return False

    source = await db.get(TenderSource, tender.source_id)
    if source is None or not is_source_sync_supported(source):
        return False

    try:
        client = GosPlanClient(base_url=source.api_url)
        detail = await client.get_purchase(tender.source_tender_id)
        await enrich_tender_from_purchase(tender, detail, db)
        await db.flush()
        logger.info('tender_processor.enriched_from_api', tender_id=str(tender.id))
        return True
    except Exception as exc:
        logger.warning('tender_processor.enrich_failed', tender_id=str(tender.id), error=str(exc))
        return False


async def _positions_text(tender_id: uuid.UUID, db: AsyncSession) -> str:
    """Текст позиций закупки для семантического анализа.

    Используется, когда документы недоступны: данные о составе закупки уже
    получены из API ГосПлан и лежат в tender_positions.
    """
    positions = (await db.execute(
        select(TenderPosition)
        .where(TenderPosition.tender_id == tender_id)
        .order_by(TenderPosition.position_number)
    )).scalars().all()
    if not positions:
        return ''
    return '\n'.join(
        f'{p.name} {p.characteristics} {p.okpd2}'.strip() for p in positions
    )[:20000]


async def _load_documents(tender_id: uuid.UUID, db: AsyncSession) -> List[TenderDocument]:
    """Загружает документы из TenderDocument.source_url, или создаёт на основе tender.source_url.
    Сохраняет файлы в S3 и заполняет storage_path."""
    existing_docs = (await db.execute(
        select(TenderDocument).where(
            TenderDocument.tender_id == tender_id,
            TenderDocument.parse_status.in_(('PENDING', 'ERROR')),
            TenderDocument.source_url != ''
        )
    )).scalars().all()
    if existing_docs:
        return existing_docs

    tender = await db.get(Tender, tender_id)
    if not tender or not tender.source_url:
        return []
    ext = os.path.splitext(tender.source_url)[1].lower()
    if ext not in ('.pdf', '.docx', '.xlsx', '.txt'):
        return []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(tender.source_url)
            response.raise_for_status()
            content = response.content
    except httpx.HTTPError as exc:
        logger.warning('tender_processor.download_failed', url=tender.source_url, error=str(exc))
        return []

    filename = os.path.basename(tender.source_url.split('?')[0])
    # Загружаем в S3
    storage_path = ''
    key = f'tenders/{str(tender_id)}/{filename}'
    success, uploaded_path = await s3_service.upload_bytes(
        key=key,
        content=content,
        content_type='application/octet-stream'
    )
    if success:
        storage_path = uploaded_path
        logger.info('tender_processor.document_uploaded_s3', tender_id=str(tender_id), key=key)
    else:
        logger.warning('tender_processor.s3_upload_failed', tender_id=str(tender_id), filename=filename)

    doc = TenderDocument(
        tender_id=tender_id,
        filename=filename,
        file_size_bytes=len(content),
        mime_type='application/octet-stream',
        source_url=tender.source_url,
        storage_path=storage_path,
        parse_status='PENDING'
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return [doc]

async def _parse_document(doc: TenderDocument) -> str:
    """Извлекает текст из сохранённого файла. Если storage_path указывает на S3, скачивает оттуда."""
    if doc.storage_path:
        if doc.storage_path.startswith('/'):
            try:
                with open(doc.storage_path, 'rb') as f:
                    content = f.read()
            except FileNotFoundError:
                return ''
        else:
            content = await s3_service.download_bytes(doc.storage_path)
            if content is None:
                logger.warning('tender_processor.s3_download_failed', storage_path=doc.storage_path)
                return ''
    else:
        # Fallback на source_url. Таймауты короткие: если внешний хост
        # недоступен, обработка не должна зависать на десятки секунд.
        try:
            timeout = httpx.Timeout(12.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(doc.source_url)
                response.raise_for_status()
                content = response.content
        except httpx.HTTPError as exc:
            logger.warning('tender_processor.document_download_failed',
                           url=doc.source_url[:120], error=str(exc))
            return ''
        except Exception as exc:
            logger.warning('tender_processor.document_download_error',
                           url=doc.source_url[:120], error=str(exc))
            return ''
    return await extract_text(doc.filename, content, doc.mime_type)

async def _semantic_filter(tender: Tender, text: str, db: AsyncSession):
    """Выполняет семантическое сравнение с категориями."""
    if not text and not tender.description:
        tender.status = 'ERROR'
        tender.processing_error = 'Нет текста для семантического анализа'
        history = TenderStatusHistory(
            tender_id=tender.id,
            status='ERROR',
            previous_status='PROCESSING',
            note='Нет текста для семантического анализа'
        )
        db.add(history)
        return

    portrait = f'{tender.title} {tender.description} {text}'[:30000]
    try:
        tender_embedding = await generate_embedding(portrait)
    except Exception as exc:
        # Сбой сервиса эмбеддингов (например, нехватка памяти в Ollama) —
        # это проблема инфраструктуры, а не данных. Тендер уже обогащён
        # позициями и описанием, поэтому не помечаем его терминальной ошибкой:
        # оставляем в UNCERTAIN, чтобы можно было повторить обработку.
        logger.error('semantic_filter.embedding_failed', error=str(exc))
        tender.status = 'UNCERTAIN'
        # Результаты предыдущих прогонов могут быть неактуальны — сбрасываем,
        # чтобы повторная обработка считалась с нуля.
        tender.embedding = None
        tender.similarity_score = None
        tender.processing_error = 'Семантический анализ не выполнен: сервис эмбеддингов недоступен (требуется повторная обработка)'
        history = TenderStatusHistory(
            tender_id=tender.id,
            status='UNCERTAIN',
            previous_status='PROCESSING',
            note='Сбой сервиса эмбеддингов, тендер оставлен для повторной обработки'
        )
        db.add(history)
        return

    tender.embedding = tender_embedding

    categories = (await db.execute(select(Category).where(Category.is_active == True))).scalars().all()
    best_score = 0.0
    best_category = None
    for cat in categories:
        if cat.embedding is not None and len(list(cat.embedding)) > 0:
            similarity = await cosine_similarity(list(tender_embedding), list(cat.embedding))
            if similarity > best_score:
                best_score = similarity
                best_category = cat

    if best_category is None:
        tender.status = 'UNCERTAIN'
        tender.matched_category_id = None
        tender.similarity_score = None
        history = TenderStatusHistory(
            tender_id=tender.id,
            status='UNCERTAIN',
            previous_status='PROCESSING',
            note='Нет активных категорий для сравнения'
        )
        db.add(history)
        return

    tender.matched_category_id = best_category.id
    tender.similarity_score = best_score

    if best_score >= 0.75:
        tender.status = 'RELEVANT'
    elif best_score >= 0.60:
        tender.status = 'UNCERTAIN'
    else:
        tender.status = 'NOT_RELEVANT'

    history = TenderStatusHistory(
        tender_id=tender.id,
        status=tender.status,
        previous_status='PROCESSING',
        note=f'Семантическое сходство с "{best_category.name}": {best_score:.2f}'
    )
    db.add(history)

async def _extract_tender_structure(tender: Tender, text: str, db: AsyncSession):
    """Извлекает позиции и требования через LLM и сохраняет в БД, предварительно удаляя старые."""
    if not text:
        return
    try:
        data = await extract_structured_data(text)
    except Exception as exc:
        logger.error('tender_processor.structure_extraction_failed', error=str(exc))
        tender.processing_error = 'Ошибка извлечения структуры'
        return

    await db.execute(delete(TenderPosition).where(TenderPosition.tender_id == tender.id))
    await db.execute(delete(TenderRequirements).where(TenderRequirements.tender_id == tender.id))

    req_data = data.get('requirements') or {}
    requirement = TenderRequirements(
        tender_id=tender.id,
        delivery_date=req_data.get('delivery_date'),
        delivery_address=req_data.get('delivery_address', ''),
        delivery_conditions=req_data.get('delivery_conditions', ''),
        license_required=req_data.get('license_required', False),
        sro_required=req_data.get('sro_required', False),
        security_bid=req_data.get('security_bid'),
        security_contract=req_data.get('security_contract'),
        prepayment_percent=req_data.get('prepayment_percent'),
        stages_count=req_data.get('stages_count', 1),
        special_conditions=req_data.get('special_conditions', [])
    )
    db.add(requirement)

    positions_data = data.get('positions') or []
    for pos in positions_data:
        position = TenderPosition(
            tender_id=tender.id,
            position_number=pos.get('position_number', 0),
            name=pos.get('name', ''),
            characteristics=pos.get('characteristics', ''),
            gost=pos.get('gost', ''),
            okpd2=pos.get('okpd2', ''),
            quantity=float(pos.get('quantity', 0)),
            unit=pos.get('unit', 'шт'),
            is_essential=True,
            notes=''
        )
        db.add(position)

    tender.structured_data = data
