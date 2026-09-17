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

# Сервисные и чужие домены: адреса с них не являются контактами поставщика
SERVICE_EMAIL_DOMAINS = {
    'example.com', 'example.org', 'example.net', 'email.com', 'site.ru', 'domain.ru',
    'mail.ru', 'yandex.ru', 'gmail.com', 'google.com', 'bk.ru', 'list.ru', 'inbox.ru',
    'avito.ru', 'youla.ru', 'ozon.ru', 'wildberries.ru', 'sberbank.ru',
    'wixpress.com', 'sentry.io', 'googlemail.com', 'yandex-team.ru',
    'demo-sait.ru', 'localhost', 'sentry-next.wixpress.com',
}

# Технические адреса, которые не имеют отношения к продажам
SERVICE_EMAIL_PREFIXES = (
    'noreply', 'no-reply', 'donotreply', 'postmaster', 'abuse', 'webmaster',
)

# Непрофильные подразделения: письма с запросом КП туда бессмысленны.
# Региональные отделы продаж (yufosales, dfosales и т.п.) сюда не входят —
# это как раз коммерческие контакты.
NON_SALES_PREFIXES = (
    'hr', 'job', 'jobs', 'vacancy', 'career', 'press', 'marketing',
    'accounting', 'buh', 'buhgalter', 'finance', 'legal', 'yurist', 'lawyer',
    'support', 'help', 'reclam', 'complaint', 'personal', 'kadry', 'kadrov',
)

# Приоритетные адреса для коммерческих запросов
SALES_PREFIX_PRIORITY = (
    'sales', 'sale', 'zakaz', 'order', 'shop', 'opt', 'trade', 'commerce',
    'commercial', 'info', 'mail', 'office', 'reception', 'post',
)


def _is_non_sales(email: str) -> bool:
    """Относится ли адрес к непрофильному подразделению."""
    local = email.rsplit('@', 1)[0].lower()
    return any(local.startswith(prefix) for prefix in NON_SALES_PREFIXES)


def _email_priority(email: str) -> int:
    """Меньше — приоритетнее для запроса коммерческого предложения."""
    local = email.rsplit('@', 1)[0].lower()
    for index, prefix in enumerate(SALES_PREFIX_PRIORITY):
        if local.startswith(prefix):
            return index
    return len(SALES_PREFIX_PRIORITY)


def _email_domain(email: str) -> str:
    return email.rsplit('@', 1)[-1].strip('.').lower()


def _same_site(email_domain: str, site_domain: str) -> bool:
    """Относится ли домен письма к сайту (учитывая поддомены)."""
    site_domain = site_domain.replace('www.', '').lower()
    if not site_domain:
        return False
    return email_domain == site_domain or email_domain.endswith('.' + site_domain)


def _extract_emails_from_html(html: str, domain: str) -> List[str]:
    """Собирает email-адреса из HTML, относящиеся к самому сайту.

    Адреса с чужих и сервисных доменов отбрасываются: раньше в базу попадали
    ``connect@avito.ru`` и ``name@example.com``, и письма уходили не поставщику.
    """
    if not html:
        return []
    pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    found = set(pattern.findall(html))
    site_domain = (domain or '').replace('www.', '').lower()

    valid: List[str] = []
    for email in found:
        email = email.strip().strip('.').lower()
        if len(email) > 80 or email.startswith(SERVICE_EMAIL_PREFIXES):
            continue
        if not re.match(r'^[^@]+@[^@]+\.[a-zа-яё]{2,}$', email):
            continue
        email_domain = _email_domain(email)
        # Только адреса на домене самого сайта: чужие и сервисные не подходят
        if email_domain in SERVICE_EMAIL_DOMAINS:
            continue
        if site_domain and not _same_site(email_domain, site_domain):
            continue
        # Кадры, бухгалтерия и пресс-служба не занимаются поставками
        if _is_non_sales(email):
            continue
        if email not in valid:
            valid.append(email)

    # Первыми — адреса, предназначенные для заказов и продаж
    valid.sort(key=_email_priority)
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
