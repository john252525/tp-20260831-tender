"""Извлечение товарных позиций, условий и документов из ответа ГосПлан API (v2).

ГосПлан отдаёт состав закупки в разных местах в зависимости от типа извещения:

* ``notificationInfo.purchaseObjectsInfo.notDrugPurchaseObjectsInfo.purchaseObject``
  — обычные товары (epNotificationEF2020 / EZK2020). ``purchaseObject`` — list или dict.
* ``notificationInfo.purchaseObjectsInfo.drugPurchaseObjectsInfo.drugPurchaseObjectInfo``
  — лекарственные препараты (ключ ``drugPurchaseObjectInfo`` — dict или list).
* ``notificationInfo.purchaseObjectsInfo.purchaseObject``
  — закупки малого объёма (epNotificationEZT2020). ``purchaseObject`` — dict или list.

Единица измерения лежит в ``OKEI`` (``nationalCode``/``name``), количество — в
``quantity.value`` (может быть ``{"undefined": "true"}``), для лекарств — ``drugQuantity``.
Код ОКПД2 берётся из ``OKPD2.OKPDCode`` либо выводится из кода КТРУ (часть до «-»).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Вспомогательные функции
# --------------------------------------------------------------------------- #

def _as_list(value: Any) -> List[Any]:
    """Нормализует значение к списку (dict -> [dict], None -> [])."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _first_dict(*candidates: Any) -> Optional[Dict[str, Any]]:
    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate
    return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(' ', '').replace(',', '.')
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _unit_from_okei(okei: Any) -> str:
    """Человекочитаемая единица измерения из блока OKEI."""
    if not isinstance(okei, dict):
        return 'шт'
    return (
        okei.get('nationalCode')
        or okei.get('name')
        or 'шт'
    )


def _okpd_from_ktru_code(code: Optional[str]) -> str:
    """ОКПД2 из кода КТРУ: '32.50.13.110-00005349' -> '32.50.13.110'."""
    if not code:
        return ''
    return str(code).split('-', 1)[0].strip()


def _fmt_value(value: Any) -> str:
    """Текстовое представление значения характеристики."""
    if value is None:
        return ''
    if isinstance(value, list):
        parts = [_fmt_value(item) for item in value]
        return ', '.join(part for part in parts if part)
    if not isinstance(value, dict):
        return str(value)

    if value.get('qualityDescription'):
        return str(value['qualityDescription'])
    if value.get('valueSet'):
        concrete = value['valueSet'].get('concreteValue')
        if concrete is not None:
            return str(concrete)
    if value.get('rangeSet'):
        value_range = (value['rangeSet'] or {}).get('valueRange') or {}
        low, high = value_range.get('min'), value_range.get('max')
        if low is not None and high is not None:
            return f'от {low} до {high}'
        if low is not None:
            return f'от {low}'
        if high is not None:
            return f'до {high}'
    if value.get('OKEI') and not any(k in value for k in ('qualityDescription', 'valueSet', 'rangeSet')):
        return ''
    return ''


def _characteristics_text(ktru: Any) -> str:
    """Собирает описание характеристик позиции из блоков КТРУ."""
    if not isinstance(ktru, dict):
        return ''
    characteristics = ktru.get('characteristics')
    if not isinstance(characteristics, dict):
        return ''

    lines: List[str] = []
    for block_key in ('characteristicsUsingReferenceInfo', 'characteristicsUsingTextForm'):
        for item in _as_list(characteristics.get(block_key)):
            if not isinstance(item, dict):
                continue
            name = (item.get('name') or '').strip()
            if not name:
                continue
            values = item.get('values') or {}
            raw_value = values.get('value') if isinstance(values, dict) else None
            text = _fmt_value(raw_value)
            if text:
                lines.append(f'{name}: {text}')
            else:
                lines.append(name)
    return '; '.join(lines)


def _extract_quantity(obj: Dict[str, Any]) -> float:
    """Количество товара.

    В извещении количество может отсутствовать (``{"undefined": "true"}``) —
    тогда оно приводится в приложении. В этом случае оцениваем его по сумме
    позиции и цене за единицу (``sum / price``).
    """
    quantity = obj.get('quantity')
    if isinstance(quantity, dict):
        if str(quantity.get('undefined', '')).lower() != 'true':
            value = _to_float(quantity.get('value'))
            if value is not None:
                return value
    else:
        value = _to_float(quantity)
        if value is not None:
            return value

    total = _to_float(obj.get('sum'))
    price = _to_float(obj.get('price'))
    if total is not None and price:
        return round(total / price, 4)
    return 0.0


def _normalize_not_drug_object(obj: Dict[str, Any]) -> Dict[str, Any]:
    ktru = obj.get('KTRU') if isinstance(obj.get('KTRU'), dict) else {}
    okpd = obj.get('OKPD2') if isinstance(obj.get('OKPD2'), dict) else {}
    return {
        'name': (obj.get('name') or ktru.get('name') or '').strip(),
        'characteristics': _characteristics_text(ktru),
        'okpd2': (okpd.get('OKPDCode') or _okpd_from_ktru_code(ktru.get('code')) or ''),
        'quantity': _extract_quantity(obj),
        'unit': _unit_from_okei(obj.get('OKEI')),
        'notes': (obj.get('KTRU') or {}).get('code') or '',
    }


def _drug_reference_info(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Справочные данные лекарства независимо от варианта упаковки ответа.

    ГосПлан использует два вида:
    * ``drugsInfo.drugInfo`` — данные одного препарата;
    * ``drugsInfo.drugInterchangeInfo.drugInterchangeReferenceInfo.drugInfo[]``
      — список взаимозаменяемых препаратов, у каждого внутри
      ``drugInfoUsingReferenceInfo``.
    """
    drugs_info = ((obj.get('objectInfoUsingReferenceInfo') or {}).get('drugsInfo') or {})

    direct = drugs_info.get('drugInfo')
    if isinstance(direct, dict):
        return direct

    interchange = drugs_info.get('drugInterchangeInfo') or {}
    # Взаимозаменяемость бывает справочной (drugInterchangeReferenceInfo)
    # или указанной вручную (drugInterchangeManualInfo).
    for key in ('drugInterchangeReferenceInfo', 'drugInterchangeManualInfo'):
        container = interchange.get(key) or {}
        for item in _as_list(container.get('drugInfo')):
            if not isinstance(item, dict):
                continue
            nested = item.get('drugInfoUsingReferenceInfo')
            if isinstance(nested, dict):
                return nested
    return {}


def _drug_text_field(drug_info: Dict[str, Any], container_key: str, field_key: str) -> str:
    """Текст поля лекарства.

    Значение может лежать как напрямую (``medicamentalFormName``), так и во
    вложенном блоке (``medicamentalFormInfo.medicamentalFormName``).
    """
    container = drug_info.get(container_key)
    if isinstance(container, dict):
        value = container.get(field_key)
        if value:
            return str(value).strip()
    value = drug_info.get(field_key)
    return str(value).strip() if value else ''


def _normalize_drug_object(obj: Dict[str, Any]) -> Dict[str, Any]:
    drug_info = _drug_reference_info(obj)
    okpd = drug_info.get('OKPD2') if isinstance(drug_info.get('OKPD2'), dict) else {}
    ktru = drug_info.get('KTRU') if isinstance(drug_info.get('KTRU'), dict) else {}

    dosage = _drug_text_field(drug_info, 'dosageInfo', 'dosageGRLSValue')
    form = _drug_text_field(drug_info, 'medicamentalFormInfo', 'medicamentalFormName')
    mnn = ((drug_info.get('MNNInfo') or {}).get('MNNName') or '').strip()
    characteristics_parts = [part for part in (mnn, form, dosage) if part]

    # Количество: total по заказчикам -> drugQuantity -> 0.
    # ``total`` — объём закупки, а ``drugQuantity`` внутри drugInterchangeInfo
    # содержит варианты взаимозаменяемых препаратов с разной дозировкой.
    quantity = None
    customers_info = obj.get('drugQuantityCustomersInfo') or {}
    if isinstance(customers_info, dict):
        quantity = _to_float(customers_info.get('total'))
    if quantity is None:
        quantity = _to_float(drug_info.get('drugQuantity'))
    if quantity is None:
        quantity = _to_float(obj.get('drugQuantity'))
    if quantity is None:
        quantity = 0.0

    return {
        'name': (obj.get('name') or drug_info.get('name') or '').strip(),
        'characteristics': ', '.join(characteristics_parts),
        'okpd2': (okpd.get('OKPDCode') or _okpd_from_ktru_code(ktru.get('code')) or ''),
        'quantity': quantity,
        'unit': _unit_from_okei(drug_info.get('manualUserOKEI')),
        'notes': ktru.get('code') or '',
    }


def _iter_purchase_objects(purchase_objects_info: Any) -> Iterable[Dict[str, Any]]:
    """Перебирает позиции независимо от варианта упаковки ответа ГосПлан."""
    if not isinstance(purchase_objects_info, dict):
        return

    not_drug = purchase_objects_info.get('notDrugPurchaseObjectsInfo')
    if isinstance(not_drug, dict):
        for obj in _as_list(not_drug.get('purchaseObject')):
            if isinstance(obj, dict):
                yield _normalize_not_drug_object(obj)

    drug = purchase_objects_info.get('drugPurchaseObjectsInfo')
    if isinstance(drug, dict):
        for obj in _as_list(drug.get('drugPurchaseObjectInfo')):
            if isinstance(obj, dict):
                yield _normalize_drug_object(obj)

    # Закупки малого объёма (EZT): purchaseObject лежит на верхнем уровне
    if 'purchaseObject' in purchase_objects_info and not isinstance(not_drug, dict):
        for obj in _as_list(purchase_objects_info.get('purchaseObject')):
            if isinstance(obj, dict):
                yield _normalize_not_drug_object(obj)


def _notification_info(purchase_detail: Dict[str, Any]) -> Dict[str, Any]:
    """Возвращает notificationInfo из первого документа извещения."""
    docs = purchase_detail.get('docs')
    for doc in _as_list(docs):
        if not isinstance(doc, dict):
            continue
        source = doc.get('source')
        if isinstance(source, dict) and isinstance(source.get('notificationInfo'), dict):
            return source['notificationInfo']
    return {}


# --------------------------------------------------------------------------- #
# Публичный API
# --------------------------------------------------------------------------- #

def _purchase_object_containers(notification: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Контейнеры с составом закупки.

    Обычно это ``notificationInfo.purchaseObjectsInfo``, но у части извещений
    (например, drugPurchaseObjectsInfo для отдельных закупок лекарств) блок
    лежит напрямую в ``notificationInfo``.
    """
    containers: List[Dict[str, Any]] = []

    purchase_objects_info = notification.get('purchaseObjectsInfo')
    if isinstance(purchase_objects_info, dict):
        containers.append(purchase_objects_info)

    has_top_level = any(
        key in notification
        for key in ('notDrugPurchaseObjectsInfo', 'drugPurchaseObjectsInfo', 'purchaseObject')
    )
    if has_top_level:
        containers.append(notification)

    return containers


def extract_positions(purchase_detail: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Список позиций закупки в формате, совместимом с моделью TenderPosition."""
    notification = _notification_info(purchase_detail)
    containers = _purchase_object_containers(notification)

    positions: List[Dict[str, Any]] = []
    dedup_index: Dict[tuple, Dict[str, Any]] = {}

    raw_objects: List[Dict[str, Any]] = []
    for container in containers:
        raw_objects.extend(_iter_purchase_objects(container))

    for obj in raw_objects:
        name = obj.get('name') or ''
        if not name:
            continue

        # Одна и та же позиция может прийти несколько раз — по одной записи
        # на каждого заказчика (customerQuantities). Такие дубли объединяем,
        # суммируя количество, а не отбрасываем.
        dedup_key = (name, obj.get('notes') or '', obj.get('unit') or '', obj.get('okpd2') or '')
        existing = dedup_index.get(dedup_key)
        if existing is not None:
            existing['quantity'] += obj.get('quantity') or 0.0
            continue

        position = {
            'position_number': len(positions) + 1,
            'name': name,
            'characteristics': obj.get('characteristics') or '',
            'gost': '',
            'okpd2': (obj.get('okpd2') or '')[:20],
            'quantity': obj.get('quantity') or 0.0,
            'unit': (obj.get('unit') or 'шт')[:50],
            'is_essential': True,
            'notes': obj.get('notes') or '',
        }
        dedup_index[dedup_key] = position
        positions.append(position)

    return positions


def extract_requirements(purchase_detail: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Базовые условия поставки из извещения (адрес, обеспечение)."""
    notification = _notification_info(purchase_detail)
    if not notification:
        return None

    delivery_address = ''
    customer_requirements = notification.get('customerRequirementsInfo') or {}
    for requirement in _as_list(customer_requirements.get('customerRequirementInfo')):
        if not isinstance(requirement, dict):
            continue
        contract_conditions = requirement.get('contractConditionsInfo') or {}
        delivery_places = contract_conditions.get('deliveryPlacesInfo') or {}
        for place in _as_list(delivery_places.get('byGARInfo')):
            if isinstance(place, dict) and place.get('deliveryPlace'):
                delivery_address = str(place['deliveryPlace'])
                break
        if not delivery_address:
            by_kladr = delivery_places.get('byKladrInfo') or {}
            for place in _as_list(by_kladr.get('kladrInfo')):
                if isinstance(place, dict) and place.get('deliveryPlace'):
                    delivery_address = str(place['deliveryPlace'])
                    break
        if delivery_address:
            break

    security_bid = _to_float(purchase_detail.get('contract_guarantee_amount'))

    return {
        'delivery_address': delivery_address,
        'delivery_conditions': '',
        'license_required': False,
        'sro_required': False,
        'security_bid': security_bid,
        'security_contract': None,
        'prepayment_percent': None,
        'stages_count': 1,
        'special_conditions': [],
    }


def extract_documents(purchase_detail: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Документы закупки из attachmentsInfo (url/fileName/fileSize)."""
    documents: List[Dict[str, Any]] = []
    for doc in _as_list(purchase_detail.get('docs')):
        if not isinstance(doc, dict):
            continue
        source = doc.get('source') or {}
        attachments = (source.get('attachmentsInfo') or {}).get('attachmentInfo')
        for attachment in _as_list(attachments):
            if not isinstance(attachment, dict):
                continue
            url = attachment.get('url') or ''
            if not url:
                continue
            documents.append(
                {
                    'filename': attachment.get('fileName') or url.split('/')[-1],
                    'url': url,
                    'file_size': _to_float(attachment.get('fileSize')),
                    'description': attachment.get('docDescription') or '',
                }
            )
    return documents


def extract_customer(purchase_detail: Dict[str, Any]) -> Dict[str, str]:
    """Наименование/ИНН/КПП заказчика."""
    notification = _notification_info(purchase_detail)
    common_info = notification.get('procedureInfo') or {}
    responsible_info = notification.get('customerRequirementsInfo') or {}

    result = {'name': '', 'inn': '', 'kpp': ''}

    for requirement in _as_list(responsible_info.get('customerRequirementInfo')):
        if not isinstance(requirement, dict):
            continue
        customer = requirement.get('customer') or {}
        if not result['name'] and customer.get('fullName'):
            result['name'] = str(customer['fullName'])
        if customer.get('INN'):
            result['inn'] = str(customer['INN'])
        if customer.get('KPP'):
            result['kpp'] = str(customer['KPP'])
        if result['name']:
            break

    if not result['name']:
        # Данные ответственного органа из commonInfo
        for doc in _as_list(purchase_detail.get('docs')):
            source = (doc or {}).get('source') or {}
            org = ((source.get('commonInfo') or {}).get('purchaseResponsibleInfo') or {})
            org_info = org.get('responsibleOrgInfo') or {}
            if org_info.get('fullName'):
                result['name'] = str(org_info['fullName'])
            result['inn'] = result['inn'] or str(org_info.get('INN') or '')
            result['kpp'] = result['kpp'] or str(org_info.get('KPP') or '')
            break

    _ = common_info
    return result


def extract_description(purchase_detail: Dict[str, Any]) -> str:
    """Описание предмета закупки."""
    notification = _notification_info(purchase_detail)
    for doc in _as_list(purchase_detail.get('docs')):
        source = (doc or {}).get('source') or {}
        common_info = source.get('commonInfo') or {}
        if common_info.get('purchaseObjectInfo'):
            return str(common_info['purchaseObjectInfo'])
    _ = notification
    object_info = purchase_detail.get('object_info')
    return str(object_info) if object_info else ''


def extract_purchase_data(purchase_detail: Dict[str, Any]) -> Dict[str, Any]:
    """Агрегирует позиции, условия, документы и заказчика из ответа ГосПлан."""
    return {
        'positions': extract_positions(purchase_detail),
        'requirements': extract_requirements(purchase_detail),
        'documents': extract_documents(purchase_detail),
        'customer': extract_customer(purchase_detail),
        'description': extract_description(purchase_detail),
    }
