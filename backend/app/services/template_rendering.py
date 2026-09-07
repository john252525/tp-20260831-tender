from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tender import Tender
from app.models.tender_position import TenderPosition
from app.models.tender_requirements import TenderRequirements
from app.services.settings_service import get_section_settings

async def render_template(template: str, context: dict) -> str:
    """Подставляет переменные {var} из контекста в шаблон."""
    for key, value in context.items():
        template = template.replace('{' + key + '}', str(value))
    return template

async def build_cp_context(tender: Tender, db: AsyncSession) -> dict:
    """Формирует контекст для шаблона запроса КП."""
    positions_result = await db.execute(
        select(TenderPosition).where(TenderPosition.tender_id == tender.id)
    )
    positions = positions_result.scalars().all()

    lines = []
    for pos in positions:
        lines.append(f"{pos.position_number}. {pos.name} - {pos.characteristics} (количество: {pos.quantity} {pos.unit})")
    positions_table = '\n'.join(lines) if lines else 'Позиции не указаны'

    total_quantity = sum(float(p.quantity) for p in positions) if positions else 0

    requirements = (await db.execute(
        select(TenderRequirements).where(TenderRequirements.tender_id == tender.id)
    )).scalar_one_or_none()

    company_settings = await get_section_settings(db, 'company') or {}

    context = {
        'lot_name': tender.title,
        'positions_table': positions_table,
        'total_quantity': total_quantity,
        'deadline_date': tender.deadline_at.strftime('%d.%m.%Y') if tender.deadline_at else 'не указан',
        'nmck': f'{float(tender.nmck):.2f}' if tender.nmck else 'не указана',
        'delivery_address': requirements.delivery_address if requirements and requirements.delivery_address else 'не указан',
        'company_name': company_settings.get('legal_name', ''),
        'contact_person': company_settings.get('contact_person', ''),
        'contact_email': company_settings.get('contact_email', ''),
        'contact_phone': company_settings.get('contact_phone', ''),
        'email_signature': company_settings.get('email_signature', ''),
        'company_signature': '\n'.join(filter(None, [
            company_settings.get('email_signature', ''),
            company_settings.get('contact_person', ''),
            company_settings.get('legal_name', ''),
            company_settings.get('contact_phone', ''),
            company_settings.get('contact_email', '')
        ])),
        'current_date': datetime.now(timezone.utc).strftime('%d.%m.%Y'),
    }
    return context
