import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
import re
import structlog
from openai import AsyncOpenAI
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.commercial_offer import CommercialOffer, OfferPosition
from app.models.tender_position import TenderPosition
from app.models.tender_requirements import TenderRequirements
from app.models.tender import Tender
from app.models.communication import Communication, CommunicationAttachment
from app.services.document_parser import extract_text
from app.services.s3_service import s3_service

logger = structlog.get_logger()

def _extract_total_price_simple(text: str) -> float:
    """Находит первую сумму в рублях в свободном тексте."""
    m = re.search(r'([\d\s]+)\s*(?:руб|₽|р\.|rub|RUB)', text, re.IGNORECASE)
    if m:
        raw = m.group(1).replace(' ', '')
        try:
            return float(raw)
        except ValueError:
            pass
    return 0.0

async def _get_client() -> AsyncOpenAI:
    if not settings.llm_api_key:
        raise RuntimeError('LLM_API_KEY is not configured')
    return AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base,
    )

async def _extract_text_from_attachment(attachment: CommunicationAttachment) -> str:
    """Извлекает текст из вложения, загружая его из S3 или локального пути."""
    content = None
    if attachment.storage_path:
        if attachment.storage_path.startswith('/'):
            try:
                with open(attachment.storage_path, 'rb') as f:
                    content = f.read()
            except FileNotFoundError:
                logger.warning('cp_parser.attachment_local_not_found', path=attachment.storage_path)
        else:
            content = await s3_service.download_bytes(attachment.storage_path)
    if content is None:
        logger.warning('cp_parser.attachment_content_empty', filename=attachment.filename)
        return ''

    try:
        return await extract_text(attachment.filename, content, attachment.mime_type)
    except Exception as exc:
        logger.warning('cp_parser.attachment_extract_failed', filename=attachment.filename, error=str(exc))
        return ''

async def parse_cp(cp_id: uuid.UUID, db: AsyncSession) -> bool:
    """Парсит коммерческое предложение, используя LLM, и сохраняет позиции и расчёты."""
    offer = await db.get(CommercialOffer, cp_id)
    if not offer:
        logger.error('cp_parser.offer_not_found', cp_id=str(cp_id))
        return False

    all_text = offer.raw_text_snippet or ''

    if offer.source_communication_id:
        comm = await db.get(Communication, offer.source_communication_id)
        if comm:
            if comm.body_text:
                all_text += '\n' + comm.body_text
            attachments_result = await db.execute(
                select(CommunicationAttachment).where(
                    CommunicationAttachment.communication_id == offer.source_communication_id
                )
            )
            attachments = attachments_result.scalars().all()
            for attachment in attachments:
                text = await _extract_text_from_attachment(attachment)
                if text:
                    all_text += '\n' + text

    if not all_text.strip():
        logger.warning('cp_parser.no_text', cp_id=str(cp_id))
        offer.status = 'ERROR'
        await db.commit()
        return False

    positions_result = await db.execute(
        select(TenderPosition).where(TenderPosition.tender_id == offer.tender_id)
    )
    tender_positions = positions_result.scalars().all()
    positions_json = [
        {
            'position_number': p.position_number,
            'name': p.name,
            'characteristics': p.characteristics,
            'quantity': float(p.quantity),
            'unit': p.unit,
            'is_essential': p.is_essential,
        } for p in tender_positions
    ]

    prompt = f"""
Ты — анализатор коммерческих предложений. Извлеки из предоставленного текста/таблицы структурированные данные.
Текст КП:
{all_text[:15000]}
Позиции тендера (для сопоставления):
{json.dumps(positions_json[:30], ensure_ascii=False)}

Извлеки строго в формате JSON:
{{
  "positions": [
    {{
      "tender_position_number": 1,
      "supplier_name": "название у поставщика",
      "match_type": "exact" | "analog" | "not_found",
      "price_per_unit": 12345.67,
      "quantity_available": 100,
      "delivery_days": 14,
      "nds_included": true,
      "nds_rate": 20,
      "notes": ""
    }}
  ],
  "delivery_terms": {{
    "delivery_address": "",
    "delivery_days": 14,
    "delivery_cost": 5000.00,
    "delivery_conditions": ""
  }},
  "payment_terms": {{
    "prepayment_percent": 30,
    "deferred_payment_days": 0,
    "description": ""
  }},
  "valid_until": "YYYY-MM-DD или null"
}}

Правила:
- match_type = "exact" если позиция полностью соответствует тендерной (тот же бренд/модель/характеристики)
- match_type = "analog" если предлагается замена с аналогичными характеристиками
- match_type = "not_found" если позиция отсутствует в КП
- Если цена не указана — price_per_unit = null
- Если НДС не указан явно — считать nds_included = true, nds_rate = 20 (для РФ)
- Все числа — без разделителей тысяч, десятичный разделитель — точка
Ответ — ТОЛЬКО JSON.
"""

    try:
        client = await _get_client()
        response = await client.chat.completions.create(
            model=settings.llm_model_chat,
            messages=[
                {"role": "system", "content": "Ты — анализатор коммерческих предложений."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
        )
        content = response.choices[0].message.content
        data = json.loads(content)
    except Exception as exc:
        logger.error('cp_parser.llm_error', error=str(exc))
        offer.status = 'ERROR'
        await db.commit()
        return False

    await db.execute(delete(OfferPosition).where(OfferPosition.commercial_offer_id == cp_id))

    total_cost = 0.0
    coverage_count = 0
    covered_tender_position_ids: Set[uuid.UUID] = set()

    for pos_data in data.get('positions', []):
        tender_pos_number = pos_data.get('tender_position_number')
        tender_pos = next((p for p in tender_positions if p.position_number == tender_pos_number), None)

        price = float(pos_data.get('price_per_unit')) if pos_data.get('price_per_unit') is not None else None
        quantity_available = float(pos_data.get('quantity_available')) if pos_data.get('quantity_available') is not None else None
        delivery_days = pos_data.get('delivery_days')
        nds_included = pos_data.get('nds_included', True)
        nds_rate = pos_data.get('nds_rate')
        supplier_name = pos_data.get('supplier_name', '')
        match_type = pos_data.get('match_type', 'not_found')
        notes = pos_data.get('notes', '')

        total_price = None
        if tender_pos and price is not None and match_type in ('exact', 'analog'):
            qty = float(tender_pos.quantity)
            total_price = price * qty
            total_cost += total_price
            coverage_count += 1
            covered_tender_position_ids.add(tender_pos.id)

        offer_pos = OfferPosition(
            commercial_offer_id=cp_id,
            tender_position_id=tender_pos.id if tender_pos else None,
            supplier_name=supplier_name,
            match_type=match_type,
            match_confidence=None,
            price_per_unit=price,
            quantity_available=quantity_available,
            delivery_days=delivery_days,
            nds_included=nds_included,
            nds_rate=nds_rate,
            total_price=total_price,
            notes=notes,
        )
        db.add(offer_pos)

    delivery_terms = data.get('delivery_terms') or {}
    payment_terms = data.get('payment_terms') or {}
    delivery_cost = float(delivery_terms.get('delivery_cost') or 0)
    total_cost_with_delivery = total_cost + delivery_cost

    req = (await db.execute(
        select(TenderRequirements).where(TenderRequirements.tender_id == offer.tender_id)
    )).scalar_one_or_none()
    security_bid_cost = float(req.security_bid) if req and req.security_bid else 0.0
    security_contract_cost = float(req.security_contract) if req and req.security_contract else 0.0
    total_cost_with_all = total_cost_with_delivery + security_bid_cost + security_contract_cost

    tender = await db.get(Tender, offer.tender_id)
    nmck = float(tender.nmck) if tender and tender.nmck else 0.0
    margin_absolute = nmck - total_cost_with_all
    margin_percent = (margin_absolute / nmck * 100) if nmck > 0 else None

    total_positions = len(tender_positions)
    coverage = (coverage_count / total_positions * 100) if total_positions > 0 else 0.0

    # Fallback: если нет позиций, извлекаем общую стоимость из текста
    if coverage == 0:
        simple_total = _extract_total_price_simple(all_text)
        if simple_total > 0:
            total_cost = simple_total
            delivery_cost = 0.0
            total_cost_with_delivery = total_cost + delivery_cost
            total_cost_with_all = total_cost_with_delivery + security_bid_cost + security_contract_cost
            margin_absolute = nmck - total_cost_with_all
            margin_percent = (margin_absolute / nmck * 100) if nmck > 0 else None
            coverage = 100.0
            # Создаём одну позицию, чтобы КП было полным
            db.add(OfferPosition(
                commercial_offer_id=cp_id,
                tender_position_id=None,
                supplier_name='Общая стоимость',
                match_type='exact',
                match_confidence=1.0,
                price_per_unit=total_cost,
                quantity_available=1,
                delivery_days=None,
                nds_included=True,
                nds_rate=20,
                total_price=total_cost,
                notes='Извлечено из свободного текста ответа'
            ))

    offer.total_cost = total_cost
    offer.delivery_cost = delivery_cost
    offer.total_cost_with_delivery = total_cost_with_delivery
    offer.total_cost_with_all = total_cost_with_all
    offer.margin_absolute = margin_absolute
    offer.margin_percent = margin_percent
    offer.payment_terms = payment_terms
    offer.delivery_terms = delivery_terms
    offer.valid_until = data.get('valid_until')
    offer.raw_text_snippet = all_text[:2000]
    offer.parsed_at = datetime.now(timezone.utc)
    offer.coverage = coverage

    if coverage >= 100:
        offer.status = 'FULL'
    elif coverage > 0:
        offer.status = 'PARTIAL'
    else:
        offer.status = 'NONE'

    clarification_items = []
    for tp in tender_positions:
        if tp.id not in covered_tender_position_ids:
            clarification_items.append(f'Отсутствует цена на позицию "{tp.name}"')
    if not delivery_cost:
        clarification_items.append('Не указана стоимость доставки')
    if not payment_terms:
        clarification_items.append('Не указаны условия оплаты')

    offer.clarification_needed = bool(clarification_items)
    offer.clarification_items = clarification_items

    await db.flush()

    # После разбора КП статус тендера мог измениться (получены полные КП,
    # достигнут порог маржи) — пересчитываем.
    try:
        from app.services.tender_status_service import recalculate_tender_status
        await recalculate_tender_status(offer.tender_id, db)
    except Exception as exc:
        logger.warning('cp_parser.status_recalc_failed', cp_id=str(cp_id), error=str(exc))

    await db.commit()
    logger.info('cp_parser.completed', cp_id=str(cp_id), status=offer.status)
    return True
