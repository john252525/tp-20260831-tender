from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import String, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, ConflictError, ValidationError
from app.models.category import Category
from app.models.task import Task
from app.schemas.categories import (
    CategoryCreateRequest, CategoryUpdateRequest, CategoryPatchRequest, BulkImportRequest
)
from app.services.embedding_service import generate_embedding

router = APIRouter()

@router.get('')
async def list_categories(
    search: Optional[str] = Query(None),
    parent_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query('name', enum=['name', 'created_at', 'updated_at']),
    sort_order: str = Query('asc', enum=['asc', 'desc']),
    db: AsyncSession = Depends(get_db)
):
    query = select(Category)
    count_query = select(func.count(Category.id))

    conditions = []
    if search:
        pattern = f'%{search}%'
        conditions.append(or_(
            Category.name.ilike(pattern),
            Category.description.ilike(pattern),
            Category.keywords.cast(String).ilike(pattern)
        ))
    if parent_id:
        conditions.append(Category.parent_id == parent_id)
    if is_active is not None:
        conditions.append(Category.is_active == is_active)

    for cond in conditions:
        query = query.where(cond)
        count_query = count_query.where(cond)

    total = (await db.execute(count_query)).scalar_one()

    sort_column = getattr(Category, sort_by, Category.name)
    if sort_order == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    categories = result.scalars().all()

    items = []
    for cat in categories:
        children_count = 0
        parent_name = None
        if cat.parent_id is None:
            children_result = await db.execute(
                select(func.count(Category.id)).where(Category.parent_id == cat.id)
            )
            children_count = children_result.scalar_one()
        else:
            parent = await db.get(Category, cat.parent_id)
            if parent:
                parent_name = parent.name

        items.append({
            'id': str(cat.id),
            'name': cat.name,
            'description': cat.description,
            'keywords': cat.keywords,
            'parent_id': str(cat.parent_id) if cat.parent_id else None,
            'parent_name': parent_name,
            'children_count': children_count,
            'is_active': cat.is_active,
            'tenders_matched_count': 0,
            'created_at': cat.created_at.isoformat(),
            'updated_at': cat.updated_at.isoformat()
        })

    pages = (total + per_page - 1) // per_page
    return {
        'success': True,
        'data': items,
        'meta': {'page': page, 'per_page': per_page, 'total': total, 'pages': pages}
    }

@router.post('', status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    parent_id = payload.parent_id
    if parent_id:
        parent = await db.get(Category, parent_id)
        if not parent:
            raise NotFoundError('Родительская категория не найдена')

    existing = await db.execute(
        select(Category).where(Category.name == payload.name, Category.parent_id == parent_id)
    )
    if existing.scalar_one_or_none():
        raise ConflictError('Категория с таким именем уже существует в этом родителе')

    category = Category(
        name=payload.name,
        description=payload.description,
        keywords=payload.keywords,
        parent_id=parent_id,
        embedding_status='generating',
    )
    db.add(category)
    await db.commit()

    result = await db.execute(select(Category).where(Category.id == category.id))
    category = result.scalar_one()

    try:
        embedding = await generate_embedding(category.description + ' ' + ' '.join(category.keywords))
        category.embedding = embedding
        category.embedding_status = 'generated'
        category.embedding_generated_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception:
        category.embedding_status = 'error'
        await db.commit()

    return {
        'success': True,
        'data': {
            'id': str(category.id),
            'name': category.name,
            'description': category.description,
            'keywords': category.keywords,
            'parent_id': str(category.parent_id) if category.parent_id else None,
            'is_active': category.is_active,
            'embedding_status': category.embedding_status,
            'embedding_generated_at': category.embedding_generated_at.isoformat() if category.embedding_generated_at else None,
            'created_at': category.created_at.isoformat(),
            'updated_at': category.updated_at.isoformat()
        }
    }

@router.post('/bulk-import', status_code=status.HTTP_202_ACCEPTED)
async def bulk_import(
    payload: BulkImportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Синхронное выполнение с сохранением задачи в БД."""
    # Валидируем все категории до вставки
    for item in payload.categories:
        parent_id = item.parent_id
        if parent_id:
            parent = await db.get(Category, parent_id)
            if not parent:
                raise NotFoundError(f'Родительская категория {parent_id} не найдена')
        existing = await db.execute(
            select(Category).where(Category.name == item.name, Category.parent_id == parent_id)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f'Категория с именем "{item.name}" уже существует')

    # Создаём категории
    created_categories = []
    for item in payload.categories:
        category = Category(
            name=item.name,
            description=item.description,
            keywords=item.keywords,
            parent_id=item.parent_id,
            embedding_status='generating'
        )
        db.add(category)
        created_categories.append(category)
    await db.commit()

    # Генерируем эмбеддинги
    embedding_errors = False
    for category in created_categories:
        try:
            embedding = await generate_embedding(category.description + ' ' + ' '.join(category.keywords))
            category.embedding = embedding
            category.embedding_status = 'generated'
            category.embedding_generated_at = datetime.now(timezone.utc)
        except Exception:
            category.embedding_status = 'error'
            embedding_errors = True
    await db.commit()

    # Сохраняем задачу как выполненную
    task = Task(
        task_type='PROCESS_TENDER',  # временный тип, не в enum OpenAPI; заменить при расширении
        status='COMPLETED',
        progress_percent=100.0,
        result_summary=f'Импортировано категорий: {len(created_categories)}' + (', с ошибками эмбеддингов' if embedding_errors else ''),
        output_data={'created_count': len(created_categories), 'embedding_errors': embedding_errors},
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return {
        'success': True,
        'data': {
            'task_id': str(task.id),
            'status': 'ACCEPTED',
            'estimated_time_seconds': 60,
            'check_url': f'/api/v1/tasks/{task.id}'
        }
    }

@router.get('/{category_id}')
async def get_category(category_id: UUID, db: AsyncSession = Depends(get_db)):
    category = await db.get(Category, category_id)
    if not category:
        raise NotFoundError('Категория не найдена')

    children_result = await db.execute(select(Category).where(Category.parent_id == category.id))
    children = children_result.scalars().all()
    children_data = [
        {'id': str(child.id), 'name': child.name, 'is_active': child.is_active}
        for child in children
    ]

    parent_name = None
    if category.parent_id:
        parent = await db.get(Category, category.parent_id)
        if parent:
            parent_name = parent.name

    return {
        'success': True,
        'data': {
            'id': str(category.id),
            'name': category.name,
            'description': category.description,
            'keywords': category.keywords,
            'parent_id': str(category.parent_id) if category.parent_id else None,
            'parent_name': parent_name,
            'children': children_data,
            'is_active': category.is_active,
            'embedding_status': category.embedding_status,
            'embedding_dimensions': 1536 if category.embedding is not None else None,
            'embedding_generated_at': category.embedding_generated_at.isoformat() if category.embedding_generated_at else None,
            'tenders_matched_count': 0,
            'created_at': category.created_at.isoformat(),
            'updated_at': category.updated_at.isoformat()
        }
    }

@router.put('/{category_id}')
async def update_category(
    category_id: UUID,
    payload: CategoryUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    category = await db.get(Category, category_id)
    if not category:
        raise NotFoundError('Категория не найдена')

    parent_id = payload.parent_id
    if parent_id:
        if parent_id == category_id:
            raise ValidationError('Категория не может быть родителем самой себе')
        parent = await db.get(Category, parent_id)
        if not parent:
            raise NotFoundError('Родительская категория не найдена')

    category.name = payload.name
    category.description = payload.description
    category.keywords = payload.keywords
    category.parent_id = parent_id
    category.embedding_status = 'generating'
    await db.commit()

    try:
        embedding = await generate_embedding(category.description + ' ' + ' '.join(category.keywords))
        category.embedding = embedding
        category.embedding_status = 'generated'
        category.embedding_generated_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception:
        category.embedding_status = 'error'
        await db.commit()

    return {'success': True, 'data': {'message': 'Категория обновлена'}}

@router.patch('/{category_id}')
async def patch_category(
    category_id: UUID,
    payload: CategoryPatchRequest,
    db: AsyncSession = Depends(get_db)
):
    category = await db.get(Category, category_id)
    if not category:
        raise NotFoundError('Категория не найдена')

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'parent_id' and value is not None:
            if value == category_id:
                raise ValidationError('Категория не может быть родителем самой себе')
            parent = await db.get(Category, value)
            if not parent:
                raise NotFoundError('Родительская категория не найдена')
        setattr(category, field, value)
        if field in ('name', 'description', 'keywords'):
            category.embedding_status = 'generating'

    await db.commit()

    if any(f in update_data for f in ('name', 'description', 'keywords')):
        try:
            embedding = await generate_embedding(category.description + ' ' + ' '.join(category.keywords))
            category.embedding = embedding
            category.embedding_status = 'generated'
            category.embedding_generated_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception:
            category.embedding_status = 'error'
            await db.commit()

    return {'success': True, 'data': {'message': 'Категория обновлена'}}

@router.delete('/{category_id}')
async def delete_category(category_id: UUID, db: AsyncSession = Depends(get_db)):
    category = await db.get(Category, category_id)
    if not category:
        raise NotFoundError('Категория не найдена')
    category.is_active = False
    await db.commit()
    return {'success': True, 'data': {'id': str(category.id), 'is_active': False}}

@router.post('/{category_id}/re-embed')
async def re_embed_category(category_id: UUID, db: AsyncSession = Depends(get_db)):
    category = await db.get(Category, category_id)
    if not category:
        raise NotFoundError('Категория не найдена')
    category.embedding_status = 'generating'
    await db.commit()
    try:
        embedding = await generate_embedding(category.description + ' ' + ' '.join(category.keywords))
        category.embedding = embedding
        category.embedding_status = 'generated'
        category.embedding_generated_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception:
        category.embedding_status = 'error'
        await db.commit()
    return {'success': True, 'data': {'embedding_status': category.embedding_status}}
