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
from app.services.tender_processor import process_tender
from app.services.llm_service import generate_search_queries
from app.services.supplier_search import search_suppliers_with_queries
from app.services.website_crawler import crawl_multiple_sites
from app.services.pipeline_progress import update_pipeline_steps, complete_pipeline_task

logger = structlog.get_logger()

STEP_LABELS = {
    'PROCESS_TENDER': 'Обработка тендера (документы, структура, скоринг)',
    'GENERATE_QUERIES': 'Генерация поисковых запросов',
    'SEARCH_SUPPLIERS': 'Поиск поставщиков',
    'CRAWL_EMAILS': 'Поиск email на сайтах поставщиков',
    'CREATE_DRAFTS': 'Создание черновиков писем',
}


def _init_steps() -> List[dict]:
    """Инициализирует список шагов."""
    return [
        {'step': step, 'status': 'WAITING', 'percent': _get_base_percent(step), 'label': label}
        for step, label in STEP_LABELS.items()
    ]


def _get_base_percent(step: str) -> int:
    mapping = {
        'PROCESS_TENDER': 10,
        'GENERATE_QUERIES': 25,
        'SEARCH_SUPPLIERS': 45,
        'CRAWL_EMAILS': 65,
        'CREATE_DRAFTS': 85,
    }
    return mapping.get(step, 0)


def _mark_step(steps: List[dict], step: str, status: str, extra: Optional[str] = None):
    """Помечает шаг статусом, сохраняя полный список steps."""
    for s in steps:
        if s['step'] == step:
            s['status'] = status
            if extra:
                s['note'] = extra
            break


def _calc_percent(steps: List[dict], active_step: str, current_percent: int) -> int:
    """Вычисляет общий процент."""
    return _get_base_percent(active_step)


async def run_full_pipeline_for_tender(
    tender_id: UUID,
    db: AsyncSession,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Выполняет все шаги пайплайна для конкретного тендера."""

    # Инициализация steps
    steps = _init_steps()

    # --- Шаг 1: Обработка тендера ---
    _mark_step(steps, 'PROCESS_TENDER', 'IN_PROGRESS')
    await update_pipeline_steps(task_id, steps, 10)
    try:
        await process_tender(tender_id, db)
    except Exception as exc:
        logger.error('pipeline.process_tender_failed', tender_id=str(tender_id), error=str(exc))
        _mark_step(steps, 'PROCESS_TENDER', 'ERROR', str(exc))
        await update_pipeline_steps(task_id, steps, 10, status='FAILED', error=str(exc))
        raise
    _mark_step(steps, 'PROCESS_TENDER', 'COMPLETED')
    await update_pipeline_steps(task_id, steps, 15)

    # Получаем тендер и его позиции
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise ValueError('Тендер не найден')

    # --- Шаг 2: Генерация поисковых запросов через LLM ---
    _mark_step(steps, 'GENERATE_QUERIES', 'IN_PROGRESS')
    await update_pipeline_steps(task_id, steps, 25)

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

    _mark_step(steps, 'GENERATE_QUERIES', 'COMPLETED', f'Сформировано {len(queries)} запросов')
    await update_pipeline_steps(task_id, steps, 35)

    # --- Шаг 3: Поиск поставщиков ---
    _mark_step(steps, 'SEARCH_SUPPLIERS', 'IN_PROGRESS')
    await update_pipeline_steps(task_id, steps, 45)

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
        _mark_step(steps, 'SEARCH_SUPPLIERS', 'ERROR', str(exc))
        await update_pipeline_steps(task_id, steps, 45, status='FAILED', error=str(exc))
        return {
            'queries': queries,
            'search_total': 0,
            'suppliers_candidates': 0,
            'websites_crawled': 0,
            'emails_found': 0,
            'drafts_created': 0,
        }

    _mark_step(steps, 'SEARCH_SUPPLIERS', 'COMPLETED', f'Найдено кандидатов: {len(candidates)}')
    await update_pipeline_steps(task_id, steps, 55)

    # --- Шаг 4: Обход сайтов и сбор email ---
    _mark_step(steps, 'CRAWL_EMAILS', 'IN_PROGRESS')
    await update_pipeline_steps(task_id, steps, 65)

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

    for c in candidates:
        c['emails'] = []
        domain = (c.get('domain') or '').replace('www.', '').lower().rstrip('.')
        if domain in email_by_domain:
            c['emails'] = email_by_domain[domain]
        # Внутренние поставщики уже имеют email в полях
        if c.get('source') == 'internal_db' and c.get('email') and c['email'] not in c.get('emails', []):
            c.setdefault('emails', [])
            if c['email'] not in c['emails']:
                c['emails'].append(c['email'])

    total_emails_found = sum(len(v) for v in email_by_domain.values()) + sum(1 for c in candidates if c.get('email'))
    _mark_step(steps, 'CRAWL_EMAILS', 'COMPLETED', f'Собрано email: {total_emails_found}')
    await update_pipeline_steps(task_id, steps, 75)

    # --- Шаг 5: Создание черновиков писем ---
    _mark_step(steps, 'CREATE_DRAFTS', 'IN_PROGRESS')
    await update_pipeline_steps(task_id, steps, 85)

    # Попробуем загрузить шаблон письма
    context = {'tender_title': tender.title, 'lot_name': tender.title}
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

    drafts_created = 0
    for sup in candidates[:10]:
        emails_to_use = [e for e in (sup.get('emails') or []) if e][:2]
        if not emails_to_use:
            continue
        for email in emails_to_use:
            existing = (await db.execute(
                select(OutgoingDraft).where(
                    OutgoingDraft.tender_id == tender_id,
                    OutgoingDraft.email == email.lower(),
                    OutgoingDraft.status == 'draft'
                )
            )).scalar_one_or_none()
            if existing:
                continue
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
                metadata_json={
                    'source': sup.get('source', 'external'),
                    'match_reason': sup.get('match_reason', ''),
                    'type': sup.get('type', 'unknown'),
                }
            )
            db.add(draft)
            drafts_created += 1

    await db.commit()

    _mark_step(steps, 'CREATE_DRAFTS', 'COMPLETED', f'Создано черновиков: {drafts_created}')
    await update_pipeline_steps(task_id, steps, 95)

    # Завершаем задачу
    if task_id:
        await complete_pipeline_task(task_id, f'Создано черновиков: {drafts_created}, email: {total_emails_found}')

    return {
        'queries': queries,
        'search_total': search_result.get('total_found', 0),
        'suppliers_candidates': len(candidates),
        'websites_crawled': len(websites),
        'emails_found': total_emails_found,
        'drafts_created': drafts_created,
    }
