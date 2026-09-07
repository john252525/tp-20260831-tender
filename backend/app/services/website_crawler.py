"""Обход сайтов поставщиков для извлечения контактных email-адресов."""
import asyncio
import re
import structlog
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Optional
import httpx

logger = structlog.get_logger()

# Таймауты и лимиты
REQUEST_TIMEOUT = 15.0
MAX_PAGES_PER_SITE = 5
# Страницы которые чаще всего содержат контакты
CONTACT_PATHS = ['', '/contacts', '/contact', '/kontakty', '/about', '/o-kompanii', '/company', '/feedback']

def _extract_emails_from_html(html: str, domain: str) -> List[str]:
    """Собирает email-адреса из HTML."""
    if not html:
        return []
    # mailto: и любые email-подобные записи
    pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    found = set(pattern.findall(html))
    # Фильтруем: исключаем общие/мусорные адреса и примеси JS
    common = {'example.com', 'example.org', 'user@email.com', 'email.com', 'site.ru'}
    valid = []
    for email in found:
        email = email.strip().strip('.').lower()
        if email in common or len(email) > 80:
            continue
        # Не берём адреса с доменами, непохожими на email (например, заканчивающиеся на цифры)
        if not re.match(r'^[^@]+@[^@]+\.[a-zа-яё]{2,}$', email):
            continue
        # Здесь ограничение: вытаскиваем только если домен похож на реальный (без пробелов)
        if email not in valid:
            valid.append(email)
    return valid[:5]


async def _fetch_page(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """Скачивает страницу и возвращает её текст."""
    try:
        response = await client.get(url, follow_redirects=True)
        if response.status_code == 200:
            # Не берём большие файлы (бинарные)
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type or 'text/plain' in content_type:
                return response.text
    except Exception as exc:
        logger.debug('website_crawler.fetch_failed', url=url, error=str(exc))
    return None


async def crawl_site_for_emails(base_url: str, max_pages: int = MAX_PAGES_PER_SITE) -> Dict[str, List[str]]:
    """Обходит указанный сайт и возвращает {url: [emails]}."""
    base_url = base_url.strip().rstrip('/')
    if not base_url.startswith(('http://', 'https://')):
        base_url = 'http://' + base_url

    results: Dict[str, List[str]] = {}
    timeout = httpx.Timeout(REQUEST_TIMEOUT, connect=8.0)
    async with httpx.AsyncClient(timeout=timeout, headers={'User-Agent': 'Mozilla/5.0 (compatible; TenderBot/1.0)'}) as client:
        parsed = urlparse(base_url)
        if not parsed.netloc:
            return results

        # Составляем список страниц
        paths_to_try = []
        for path in CONTACT_PATHS[:max_pages]:
            paths_to_try.append(urljoin(base_url, path) if path else base_url)

        count = 0
        for url in paths_to_try:
            if count >= max_pages:
                break
            html = await _fetch_page(client, url)
            if not html:
                continue
            emails = _extract_emails_from_html(html, parsed.netloc)
            if emails:
                results[url] = emails
            count += 1

            # Ищем ссылки на страницы "контакты" на главной
            if url == base_url and count < max_pages:
                for match in re.finditer(r'href=["\']([^"\']*)["\']', html, re.IGNORECASE):
                    link = match.group(1)
                    if any(term in link.lower() for term in ['contact', 'kontakt', 'feedback', 'about', 'company']):
                        full_link = urljoin(base_url, link)
                        if full_link not in paths_to_try:
                            paths_to_try.append(full_link)
    return results


async def crawl_multiple_sites(urls: List[str], limit_sites: int = 10) -> List[Dict[str, any]]:
    """Обходит несколько сайтов и собирает email-адреса.
    Возвращает список: [{'website': original_url, 'domain': domain, 'emails': [...]}, ...]
    """
    if not urls:
        return []

    all_results: List[Dict[str, any]] = []
    semaphore = asyncio.Semaphore(3)  # до 3 параллельных запросов

    async def _crawl_one(url: str):
        async with semaphore:
            try:
                site_emails = await crawl_site_for_emails(url, max_pages=MAX_PAGES_PER_SITE)
                consolidated = []
                for page_emails in site_emails.values():
                    for e in page_emails:
                        if e not in consolidated:
                            consolidated.append(e)
                if consolidated:
                    parsed = urlparse(url if url.startswith('http') else 'http://' + url)
                    domain = parsed.netloc.replace('www.', '').split(':')[0]
                    all_results.append({
                        'website': url,
                        'domain': domain,
                        'emails': consolidated,
                    })
            except Exception as exc:
                logger.warning('website_crawler.site_crawl_failed', url=url, error=str(exc))

    await asyncio.gather(*[_crawl_one(url) for url in urls[:limit_sites]])
    return all_results
