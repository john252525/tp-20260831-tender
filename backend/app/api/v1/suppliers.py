import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import String, select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, ConflictError
from app.models.supplier import Supplier
from app.models.lot_supplier import LotSupplier
from app.schemas.suppliers import SupplierCreateRequest, SupplierUpdateRequest

router = APIRouter()

@router.get('')
async def list_suppliers(
    search: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    has_email: Optional[bool] = Query(None),
    has_phone: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(None),
    min_successful_deals: Optional[int] = Query(None, ge=0),
    created_after: Optional[datetime] = Query(None),
    sort_by: str = Query('created_at', enum=['name', 'created_at', 'successful_deals', 'total_volume_rub']),
    sort_order: str = Query('desc', enum=['asc', 'desc']),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(Supplier)
    count_query = select(func.count(Supplier.id))
    conditions = []

    if search:
        pattern = f'%{search}%'
        conditions.append(or_(
            Supplier.name.ilike(pattern),
            Supplier.email.ilike(pattern),
            Supplier.inn.ilike(pattern),
            Supplier.phone.ilike(pattern)
        ))
    if type:
        conditions.append(Supplier.type == type)
    if tags:
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        tag_conditions = []
        for tag in tag_list:
            tag_conditions.append(Supplier.tags.cast(String).ilike(f'%{tag}%'))
        if tag_conditions:
            conditions.append(or_(*tag_conditions))
    if has_email is not None:
        if has_email:
            conditions.append(Supplier.email != '')
        else:
            conditions.append(Supplier.email == '')
    if has_phone is not None:
        if has_phone:
            conditions.append(Supplier.phone != '')
        else:
            conditions.append(Supplier.phone == '')
    if is_active is not None:
        conditions.append(Supplier.is_active == is_active)
    if min_successful_deals is not None:
        conditions.append(Supplier.successful_deals >= min_successful_deals)
    if created_after:
        conditions.append(Supplier.created_at >= created_after)

    for cond in conditions:
        query = query.where(cond)
        count_query = count_query.where(cond)

    total = (await db.execute(count_query)).scalar_one()

    sort_column = getattr(Supplier, sort_by, Supplier.created_at)
    if sort_order == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    suppliers = result.scalars().all()

    items = []
    for s in suppliers:
        items.append({
            'id': str(s.id),
            'name': s.name,
            'type': s.type,
            'website': s.website,
            'email': s.email,
            'phone': s.phone,
            'telegram': s.telegram,
            'inn': s.inn,
            'tags': s.tags,
            'rating': s.rating,
            'total_lots': s.total_lots,
            'successful_deals': s.successful_deals,
            'total_volume_rub': float(s.total_volume_rub) if s.total_volume_rub else 0.0,
            'is_active': s.is_active,
            'created_at': s.created_at.isoformat(),
            'updated_at': s.updated_at.isoformat()
        })

    pages = (total + per_page - 1) // per_page
    return {'success': True, 'data': items, 'meta': {'page': page, 'per_page': per_page, 'total': total, 'pages': pages}}

@router.post('', status_code=status.HTTP_201_CREATED)
async def create_supplier(payload: SupplierCreateRequest, db: AsyncSession = Depends(get_db)):
    unique_checks = []
    if payload.email:
        unique_checks.append(Supplier.email == payload.email)
    if payload.phone:
        unique_checks.append(Supplier.phone == payload.phone)
    if payload.inn:
        unique_checks.append(Supplier.inn == payload.inn)
    if unique_checks:
        existing = await db.execute(select(Supplier).where(or_(*unique_checks)))
        duplicate = existing.scalar_one_or_none()
        if duplicate:
            raise ConflictError('Поставщик с такими данными уже существует')

    supplier = Supplier(
        name=payload.name,
        type=payload.type,
        website=payload.website,
        email=payload.email or '',
        phone=payload.phone,
        telegram=payload.telegram,
        whatsapp=payload.whatsapp,
        contact_persons=[cp.model_dump() for cp in payload.contact_persons],
        inn=payload.inn,
        kpp=payload.kpp,
        ogrn=payload.ogrn,
        legal_address=payload.legal_address,
        tags=payload.tags,
        notes=payload.notes,
    )
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return {'success': True, 'data': {
        'id': str(supplier.id),
        'name': supplier.name,
        'type': supplier.type,
        'website': supplier.website,
        'email': supplier.email,
        'phone': supplier.phone,
        'telegram': supplier.telegram,
        'whatsapp': supplier.whatsapp,
        'inn': supplier.inn,
        'kpp': supplier.kpp,
        'ogrn': supplier.ogrn,
        'legal_address': supplier.legal_address,
        'contact_persons': supplier.contact_persons,
        'tags': supplier.tags,
        'notes': supplier.notes,
        'rating': supplier.rating,
        'total_lots': supplier.total_lots,
        'successful_deals': supplier.successful_deals,
        'total_volume_rub': float(supplier.total_volume_rub) if supplier.total_volume_rub else 0.0,
        'is_active': supplier.is_active,
        'created_at': supplier.created_at.isoformat(),
        'updated_at': supplier.updated_at.isoformat()
    }}

@router.get('/{supplier_id}')
async def get_supplier(supplier_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    supplier = await db.get(Supplier, supplier_id)
    if not supplier:
        raise NotFoundError('Поставщик не найден')

    total_lots = (await db.execute(select(func.count(LotSupplier.id)).where(LotSupplier.supplier_id == supplier.id))).scalar_one()
    successful_deals = supplier.successful_deals
    total_volume = float(supplier.total_volume_rub) if supplier.total_volume_rub else 0.0
    recent_tenders = []

    return {
        'success': True,
        'data': {
            'id': str(supplier.id),
            'name': supplier.name,
            'type': supplier.type,
            'website': supplier.website,
            'contacts': {
                'email': supplier.email,
                'phone': supplier.phone,
                'telegram': supplier.telegram,
                'whatsapp': supplier.whatsapp,
                'contact_persons': supplier.contact_persons,
            },
            'legal_info': {
                'inn': supplier.inn,
                'kpp': supplier.kpp,
                'ogrn': supplier.ogrn,
                'legal_address': supplier.legal_address,
            },
            'tags': supplier.tags,
            'notes': supplier.notes,
            'rating': supplier.rating,
            'statistics': {
                'total_lots': total_lots,
                'cp_received': 0,
                'successful_deals': successful_deals,
                'total_volume_rub': total_volume,
            },
            'recent_tenders': recent_tenders,
            'is_active': supplier.is_active,
            'deleted_at': supplier.deleted_at.isoformat() if supplier.deleted_at else None,
            'created_at': supplier.created_at.isoformat(),
            'updated_at': supplier.updated_at.isoformat()
        }
    }

@router.patch('/{supplier_id}')
async def update_supplier(supplier_id: uuid.UUID, payload: SupplierUpdateRequest, db: AsyncSession = Depends(get_db)):
    supplier = await db.get(Supplier, supplier_id)
    if not supplier:
        raise NotFoundError('Поставщик не найден')
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'contact_persons':
            supplier.contact_persons = [cp if isinstance(cp, dict) else cp.model_dump() for cp in value]
        elif field == 'tags':
            supplier.tags = value
        else:
            setattr(supplier, field, value)
    await db.commit()
    return {'success': True, 'data': {'message': 'Поставщик обновлён'}}

@router.delete('/{supplier_id}')
async def delete_supplier(supplier_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    supplier = await db.get(Supplier, supplier_id)
    if not supplier:
        raise NotFoundError('Поставщик не найден')
    supplier.is_active = False
    supplier.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {'success': True, 'data': {'id': str(supplier.id), 'is_active': False, 'deleted_at': supplier.deleted_at.isoformat() if supplier.deleted_at else None}}

@router.post('/merge')
async def merge_suppliers(payload: dict, db: AsyncSession = Depends(get_db)):
    primary_id = payload.get('primary_id')
    secondary_id = payload.get('secondary_id')
    if not primary_id or not secondary_id:
        raise ConflictError('Необходимо указать primary_id и secondary_id')
    if primary_id == secondary_id:
        raise ConflictError('primary_id и secondary_id не должны совпадать')

    primary = await db.get(Supplier, primary_id)
    secondary = await db.get(Supplier, secondary_id)
    if not primary or not secondary:
        raise NotFoundError('Поставщик не найден')

    # Перенос LotSupplier с secondary на primary с обработкой возможных дубликатов
    lots = (await db.execute(select(LotSupplier).where(LotSupplier.supplier_id == secondary_id))).scalars().all()
    for lot in lots:
        existing_lot = await db.execute(
            select(LotSupplier).where(
                LotSupplier.tender_id == lot.tender_id,
                LotSupplier.supplier_id == primary_id
            )
        )
        if existing_lot.scalar_one_or_none():
            # Просто удаляем дубликат, оставляя запись у primary
            db.delete(lot)
        else:
            lot.supplier_id = primary_id

    # Обновляем агрегаты primary
    primary.total_lots += secondary.total_lots
    primary.successful_deals += secondary.successful_deals
    primary.total_volume_rub = float(primary.total_volume_rub or 0) + float(secondary.total_volume_rub or 0)
    # Деактивируем secondary
    secondary.is_active = False
    secondary.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {'success': True, 'data': {'message': 'Поставщики объединены'}}

@router.get('/{supplier_id}/communications')
async def supplier_communications(
    supplier_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    supplier = await db.get(Supplier, supplier_id)
    if not supplier:
        raise NotFoundError('Поставщик не найден')
    # Заглушка: пока нет модели Communication
    return {'success': True, 'data': [], 'meta': {'page': page, 'per_page': per_page, 'total': 0, 'pages': 0}}
