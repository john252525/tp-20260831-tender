# Iteration 005 — Качество поставщиков
Date: 2026-09-16

## Goal
11 из 14 поставщиков — мусор. Письма уходили на connect@avito.ru, name@example.com.

## Changes
- backend/app/services/website_crawler.py — письма только с домена сайта,
  отсев сервисных доменов, бесплатной почты, непрофильных подразделений,
  приоритет коммерческих адресов
- backend/app/services/supplier_search.py — имя из домена вместо SEO-заголовка,
  отсев маркетплейсов, устойчивость _deduplicate и _extract_domain к None

## Tests
- backend/tests/test_website_crawler.py (6)
- test_supplier_search.py переписан (импортировал удалённую _search_google)

## Notes / next
- Почищено 16 мусорных черновиков
