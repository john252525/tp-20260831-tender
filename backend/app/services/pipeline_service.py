"""Сервис полного пайплайна обработки тендера:
1. process_tender (скачивание документов, структура, скоринг)
2. Генерация поисковых запросов (через LLM)
3. Поиск поставщиков
4. Обход сайтов и сбор email
5. Формирование черновиков писем поставщикам
"""
import structlog
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.tender import Tender
from app.models.tender_position import TenderPosition
from app.models.outgoing_draft import OutgoingDraft
from app.models.task import Task as TaskModel
from app.services.tender_processor import process_tender
from app.services.llm_service import generate_search_queries
from app.services.supplier_search import search_suppliers_with_queries
from app.services.website_crawler import crawl_multiple_sites

logger = structlog.get_logger()

# Этапы конвейера
PIPELINE_STEPS = [
    'PROCESS_TENDER',
    'GENERATE_QUERIES',
    'SEARCH_SUPPLIERS',
    'CRAWL_EMAILS',
    'CREATE_DRAFTS',
]

async def _update_pipeline_progress(
    db: AsyncSession,
    task_id: Optional[str],
    step: str,
    percent: float,
    status: str = 'IN_PROGRESS',
    error: str = None,
):
    """Обновить прогресс по шагам и сохранить в БД."""
    if not task_id:
        return
    task = await db.get(TaskModel, UUID(task_id))
    if not task:
        return

    steps = []
    if task.output_data:
        steps = task.output_data.get('steps', [])

    found = False
    for s in steps:
        if s.get('step') == step:
            s['status'] = 'ERROR' if error else status
            s['percent'] = percent
            if error:
                s['error'] = error
            found = True
            break
    if not found:
        step_entry = {
            'step': step,
            'status': 'ERROR' if error else status,
            'percent': percent,
        }
        if error:
            step_entry['error'] = error
        steps.append(step_entry)

    task.output_data = {'steps': steps}
    task.progress_percent = percent
    if error:
        task.status = 'FAILED'
        task.error_message = error[:2000]
        task.completed_at = datetime.now(timezone.utc)
    await db.commit()


async def run_full_pipeline_for_tender(
    tender_id: UUID,
    db: AsyncSession,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Выполняет все шаги пайплайна для конкретного тендера."""

    # --- Шаг 1: Обработка тендера ---
    await _update_pipeline_progress(db, task_id, 'PROCESS_TENDER', 10)
    try:
        await process_tender(tender_id, db)
    except Exception as exc:
        logger.error('pipeline.process_tender_failed', tender_id=str(tender_id), error=str(exc))
        await _update_pipeline_progress(db, task_id, 'PROCESS_TENDER', 10, status='ERROR', error=str(exc))
        raise

    tender = await db.get(Tender, tender_id)
    if not tender:
        raise ValueError('Тендер не найден')

    # --- Шаг 2: Генерация поисковых запросов через LLM ---
    await _update_pipeline_progress(db, task_id, 'GENERATE_QUERIES', 25)

    positions_result = await db.execute(
        select(TenderPosition).where(TenderPosition.tender_id == tender_id)
    )
    positions = positions_result.scalars().all()
    positions_data = []
    for p in positions:
        positions_data.append({
            'name': p.name,
            'characteristics': p.characteristics or '',
            'quantity': float(p.quantity) if p.quantity else None,
            'unit': p.unit,
        })

    # Импортируем оффлайн-фолбек для генерации запросов
    if positions_data:
        fallback_queries = [f"{p['name']} оптом поставщик" for p in positions_data[:5]]
    else:
        fallback_queries = [f"{tender.title[:200]} поставщик"]

    queries = list(fallback_queries)
    try:
        generated = await generate_search_queries(
            tender_title=tender.title,
            description=tender.description or '',
            positions=positions_data,
            region=''
        )
        normalized = []
        for q in generated:
            if isinstance(q, dict):
                text = q.get('query') or q.get('q') or ''
                if text:
                    normalized.append(text)
            elif isinstance(q, str) and q.strip():
                normalized.append(q.strip())
        if normalized:
            queries = normalized[:10]
    except Exception as exc:
        logger.warning('pipeline.queries_llm_fallback', error=str(exc))

    tender.search_queries = queries
    await db.commit()

    # --- Шаг 3: Поиск поставщиков ---
    await _update_pipeline_progress(db, task_id, 'SEARCH_SUPPLIERS', 45)

    search_result: Dict[str, Any] = {}
    candidates = []
    try:
        search_result = await search_suppliers_with_queries(
            tender_id=tender_id,
            queries=queries,
            max_suppliers=10,
            channels=['external', 'internal_db'],
            db=db,
        )
        candidates = search_result.get('results', [])
    except Exception as exc:
        logger.error('pipeline.search_suppliers_failed', error=str(exc))
        await _update_pipeline_progress(db, task_id, 'SEARCH_SUPPLIERS', 45, status='ERROR', error=str(exc))
        return {
            'queries': queries,
            'search_total': 0,
            'suppliers_candidates': 0,
            'websites_crawled': 0,
            'emails_found': 0,
            'drafts_created': 0,
        }

    # --- Шаг 4: Обход сайтов и сбор email ---
    await _update_pipeline_progress(db, task_id, 'CRAWL_EMAILS', 65)

    # Извлекаем уникальные сайты из кандидатов
    websites = []
    seen_sites = set()
    for c in candidates:
        url = c.get('website') or c.get('domain') or ''
        if not url:
            continue
        norm = url.replace('http://', '').replace('https://', '').replace('www.', '').rstrip('/').lower()
        if norm and norm not in seen_sites:
            seen_sites.add(norm)
            websites.append(url if url.startswith('http') else 'http://' + url)

    site_emails: List[Dict[str, Any]] = []
    try:
        site_emails = await crawl_multiple_sites(websites, limit_sites=8)
    except Exception as exc:
        logger.warning('pipeline.crawl_failed', error=str(exc))

    email_by_domain: Dict[str, List[str]] = {}
    for item in site_emails:
        domain = (item.get('domain') or '').replace('www.', '').lower().rstrip('.')
        if domain and item.get('emails'):
            email_by_domain[domain] = list(item['emails'])

    # Проставляем email кандидатам по доменам
    for c in candidates:
        c['emails'] = []
        domain = (c.get('domain') or '').replace('www.', '').lower().rstrip('.')
        if domain in email_by_domain:
            c['emails'] = email_by_domain[domain]
        # Если email не найден, можно попробовать domain как email
        if not c['emails'] and c.get('source') == 'internal_db':
            # Для внутренних поставщиков email уже есть
            pass

    # --- Шаг 5: Создание черновиков писем ---
    await _update_pipeline_progress(db, task_id, 'CREATE_DRAFTS', 85)

    # Попробуем загрузить шаблон письма
    try:
        from app.services.template_rendering import build_cp_context
        from app.services.settings_service import get_section_settings
        templates_settings = await get_section_settings(db, 'templates') or {}
        cp_template = templates_settings.get('cp_request', {})
        context = await build_cp_context(tender, db)
    except Exception:
        cp_template = {}
        context = {'tender_title': tender.title, 'lot_name': tender.title}

    subject_template = cp_template.get('subject', 'Запрос коммерческого предложения: {lot_name}')
    body_template = cp_template.get('body', 'Добрый день!\n\nПросим направить коммерческое предложение по тендеру "{lot_name}".\n\nС уважением,\n{company_signature}')

    # Найдём email для внутренних БД-кандидатов, где поле email не пустое
    for c in candidates:
        if c.get('source') == 'internal_db' and c.get('email'):
            c.setdefault('emails', [])
            if c['email'] not in c['emails']:
                c['emails'].append(c['email'])

    drafts_created = 0
    for sup in candidates[:10]:  # максимум 10 кандидатов
        no_email = not sup.get('emails') or all(not e for e in sup['emails'])
        if no_email:
            continue
        emails_to_use = [e for e in sup['emails'] if e][:2]  # до 2 email с сайта

        for email in emails_to_use:
            # Проверяем существующий черновик
            existing = (await db.execute(
                select(OutgoingDraft).where(
                    OutgoingDraft.tender_id == tender_id,
                    OutgoingDraft.email == email.lower(),
                    OutgoingDraft.status == 'draft'
                )
            )).scalar_one_or_none()
            if existing:
                continue

            # Рендерим письмо
            subject = subject_template
            body = body_template
            for k, v in context.items():
                subject = subject.replace('{' + k + '}', str(v))
                body = body.replace('{' + k + '}', str(v))

            draft = OutgoingDraft(
                tender_id=tender_id,
                supplier_website=sup.get('website') or sup.get('domain') or '',
                supplier_name=sup.get('name', ''),
                email=email.lower(),
                subject=subject,
                body_text=body,
                status='draft',
                metadata={
                    'source': sup.get('source', 'external'),
                    'match_reason': sup.get('match_reason', ''),
                    'type': sup.get('type', 'unknown'),
                    'search_total': search_result.get('total_found', 0),
                }
            )
            db.add(draft)
            drafts_created += 1

    await db.commit()

    total_emails_found = sum(len(v) for v in email_by_domain.values()) + sum(1 for c in candidates if c.get('email'))
    await _update_pipeline_progress(db, task_id, 'CREATE_DRAFTS', 95)

    # Помечаем задачу завершённой
    if task_id:
        task = await db.get(TaskModel, UUID(task_id))
        if task:
            task.status = 'COMPLETED'
            task.progress_percent = 100.0
            task.completed_at = datetime.now(timezone.utc)
            task.result_summary = f'Создано черновиков: {drafts_created}, email: {total_emails_found}'
            await db.commit()

    return {
        'queries': queries,
        'search_total': search_result.get('total_found', 0),
        'suppliers_candidates': len(candidates),
        'websites_crawled': len(websites),
        'emails_found': total_emails_found,
        'drafts_created': drafts_created,
    }
