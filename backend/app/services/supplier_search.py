import re
from typing import List, Dict, Any, Set
from urllib.parse import urlparse
import uuid
import structlog
import httpx
from sqlalchemy import select, or_, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.tender import Tender
from app.models.tender_position import TenderPosition
from app.models.category import Category
from app.models.supplier import Supplier

logger = structlog.get_logger()

async def search_suppliers_for_tender(
    tender_id: uuid.UUID,
    max_suppliers: int = 10,
    channels: List[str] = ['google', 'internal_db'],
    priority_order: List[str] = ['manufacturer', 'distributor', 'wholesaler'],
    db: AsyncSession = None
) -> Dict[str, Any]:
    """
    Поиск поставщиков для тендера.
    Возвращает словарь с результатами и метаданными.
    """
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise ValueError('Тендер не найден')

    positions_result = await db.execute(
        select(TenderPosition).where(TenderPosition.tender_id == tender_id)
    )
    positions = positions_result.scalars().all()

    queries = await _generate_search_queries(tender, positions)

    all_found = []
    if 'google' in channels or 'external' in channels:
        all_found.extend(await _search_external(queries))
    if 'internal_db' in channels:
        all_found.extend(await _search_internal(tender, positions, db))

    total_found = len(all_found)
    deduped = _deduplicate(all_found)
    after_dedup = len(deduped)
    prioritized = _prioritize(deduped, priority_order)
    after_priority_filter = len(prioritized)

    top_results = prioritized[:max_suppliers]

    return {
        'search_queries_used': queries,
        'total_found': total_found,
        'after_dedup': after_dedup,
        'after_priority_filter': after_priority_filter,
        'results': top_results,
    }

async def _generate_search_queries(tender: Tender, positions: List[TenderPosition]) -> List[str]:
    queries = []
    if positions:
        for pos in positions[:5]:
            name = pos.name.strip()
            if name:
                queries.append(f'{name} оптом')
                queries.append(f'{name} поставщик')
                queries.append(f'{name} производитель')
                queries.append(f'{name} дистрибьютор')
    else:
        title = tender.title.strip()
        if title:
            queries.append(f'{title} поставщик')
            queries.append(f'{title} оптом')
    return queries[:10]

async def _search_external(queries: List[str]) -> List[Dict[str, Any]]:
    """Выполняет поиск через внешний API (2222.apitter.com) и возвращает кандидатов."""
    if not settings.search_api_url:
        logger.warning('supplier_search.search_api_url_missing')
        return []

    candidates = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for query in queries[:3]:
            try:
                response = await client.get(settings.search_api_url, params={'q': query})
                response.raise_for_status()
                data = response.json()
                if not data.get('success'):
                    logger.warning('supplier_search.api_error', query=query, response=data)
                    continue
                items = data.get('results', [])
                for item in items:
                    url = item.get('url', '')
                    domain = _extract_domain(url)
                    if not domain:
                        continue
                    candidates.append({
                        'name': item.get('title', domain),
                        'website': url,
                        'email': '',
                        'phone': '',
                        'source': 'google',  # сохраняем source google для совместимости
                        'relevance': 'medium',
                        'match_reason': f'Найден по запросу "{query}"',
                        'is_new': True,
                        'already_in_db': False,
                        'selected': False,
                        'type': 'unknown',
                        'domain': domain,
                    })
            except httpx.HTTPError as exc:
                logger.warning('supplier_search.external_request_failed', query=query, error=str(exc))

    return candidates

async def _search_internal(tender: Tender, positions: List[TenderPosition], db: AsyncSession) -> List[Dict[str, Any]]:
    """Ищет поставщиков во внутренней базе по тегам категории тендера."""
    if not tender.matched_category_id:
        return []

    category = await db.get(Category, tender.matched_category_id)
    if not category or not category.keywords:
        return []

    keywords = category.keywords
    conditions = []
    for kw in keywords:
        conditions.append(Supplier.tags.cast(String).ilike(f'%{kw}%'))

    if not conditions:
        return []

    result = await db.execute(
        select(Supplier).where(
            Supplier.is_active == True,
            or_(*conditions)
        )
    )
    suppliers = result.scalars().all()

    candidates = []
    for s in suppliers:
        domain = _extract_domain(s.website)
        candidates.append({
            'id': str(s.id),
            'name': s.name,
            'website': s.website,
            'email': s.email,
            'phone': s.phone,
            'source': 'internal_db',
            'relevance': 'high',
            'match_reason': f'Найден по ключевым словам категории: {keywords[:3]}',
            'is_new': False,
            'already_in_db': True,
            'selected': False,
            'type': s.type,
            'domain': domain,
        })
    return candidates

def _extract_domain(url: str) -> str:
    """Извлекает домен второго уровня из URL."""
    if not url:
        return ''
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host.startswith('www.'):
            host = host[4:]
        parts = host.split('.')
        if len(parts) >= 2:
            return '.'.join(parts[-2:])
        return host
    except Exception:
        return ''

def _deduplicate(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Убирает дубликаты по домену, email, inn, телефону."""
    seen_identifiers: Set[str] = set()
    unique = []
    for cand in candidates:
        identifiers = []
        domain = cand.get('domain', '')
        if domain:
            identifiers.append(f'domain:{domain}')
        email = cand.get('email', '').lower()
        if email:
            identifiers.append(f'email:{email}')
        inn = cand.get('inn', '')
        if inn:
            identifiers.append(f'inn:{inn}')
        phone = cand.get('phone', '')
        if phone:
            normalized_phone = re.sub(r'\D', '', phone)
            identifiers.append(f'phone:{normalized_phone}')

        if not identifiers:
            unique.append(cand)
            continue

        is_duplicate = any(identifier in seen_identifiers for identifier in identifiers)
        if not is_duplicate:
            for identifier in identifiers:
                seen_identifiers.add(identifier)
            unique.append(cand)
    return unique

def _prioritize(candidates: List[Dict[str, Any]], priority_order: List[str]) -> List[Dict[str, Any]]:
    """Сортирует кандидатов по типу и релевантности."""
    type_priority = {t: i for i, t in enumerate(priority_order)}
    relevance_priority = {'high': 0, 'medium': 1, 'low': 2}

    def sort_key(cand):
        type_rank = type_priority.get(cand.get('type', 'unknown'), len(type_priority))
        relevance_rank = relevance_priority.get(cand.get('relevance', 'medium'), 1)
        source_rank = 0 if cand.get('source') == 'internal_db' else 1
        return (type_rank, relevance_rank, source_rank)

    return sorted(candidates, key=sort_key)
