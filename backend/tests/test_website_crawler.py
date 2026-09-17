"""Тесты извлечения контактов с сайтов поставщиков."""

from app.services.website_crawler import (
    _email_priority,
    _extract_emails_from_html,
    _is_non_sales,
)


def test_emails_from_other_domains_are_rejected():
    """Адреса с чужих доменов не попадают в контакты поставщика.

    Раньше в базу попадали connect@avito.ru и name@example.com.
    """
    html = """
    <a href="mailto:sales@perchatki21.ru">Написать</a>
    <span>connect@avito.ru</span>
    <span>name@example.com</span>
    """
    emails = _extract_emails_from_html(html, 'perchatki21.ru')
    assert emails == ['sales@perchatki21.ru']


def test_service_and_free_mail_domains_are_rejected():
    """Адреса на бесплатных и сервисных доменах отбрасываются."""
    html = """
    <span>info@perchatki21.ru</span>
    <span>director@gmail.com</span>
    <span>noreply@perchatki21.ru</span>
    """
    emails = _extract_emails_from_html(html, 'perchatki21.ru')
    assert emails == ['info@perchatki21.ru']


def test_subdomain_emails_are_accepted():
    """Адреса на поддомене сайта относятся к этому же поставщику."""
    emails = _extract_emails_from_html(
        '<span>sales@shop.perchatki21.ru</span>', 'perchatki21.ru'
    )
    assert emails == ['sales@shop.perchatki21.ru']


def test_non_sales_departments_are_rejected():
    """Кадры, бухгалтерия и пресса не занимаются поставками."""
    assert _is_non_sales('hr@company.ru')
    assert _is_non_sales('buhgalter@company.ru')
    assert _is_non_sales('marketing@company.ru')
    # Региональные отделы продаж — коммерческие контакты
    assert not _is_non_sales('sales@company.ru')
    assert not _is_non_sales('yufosales@company.ru')
    assert not _is_non_sales('zakaz@company.ru')


def test_sales_addresses_have_priority():
    """Первыми отдаются адреса для заказов, а не общие."""
    html = """
    <span>reception@company.ru</span>
    <span>zakaz@company.ru</span>
    <span>mail@company.ru</span>
    """
    emails = _extract_emails_from_html(html, 'company.ru')
    assert emails[0] == 'zakaz@company.ru'
    assert _email_priority('sales@company.ru') < _email_priority('info@company.ru')


def test_empty_html_returns_nothing():
    assert _extract_emails_from_html('', 'company.ru') == []
    assert _extract_emails_from_html('<html></html>', 'company.ru') == []
