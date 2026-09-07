import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.api_token import ApiToken
from app.schemas.common import PaginationMeta
from app.schemas.tokens import ApiTokenCreateRequest, ApiTokenUpdateRequest

router = APIRouter()

@router.get('')
async def list_tokens(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    offset = (page - 1) * per_page
    total = (await db.execute(select(func.count(ApiToken.id)))).scalar_one()
    result = await db.execute(select(ApiToken).order_by(ApiToken.created_at.desc()).offset(offset).limit(per_page))
    tokens = result.scalars().all()
    items = []
    for t in tokens:
        preview = f'{t.token[:4]}...{t.token[-4:]}' if len(t.token) > 8 else t.token
        items.append({
            'id': str(t.id),
            'description': t.description,
            'token_preview': preview,
            'is_active': t.is_active,
            'rate_limit_per_minute': t.rate_limit_per_minute,
            'last_used_at': t.last_used_at.isoformat() if t.last_used_at else None,
            'expires_at': t.expires_at.isoformat() if t.expires_at else None,
            'created_at': t.created_at.isoformat(),
            'updated_at': t.updated_at.isoformat()
        })
    pages = (total + per_page - 1) // per_page
    return {
        'success': True,
        'data': items,
        'meta': {'page': page, 'per_page': per_page, 'total': total, 'pages': pages}
    }

@router.post('', status_code=201)
async def create_token(
    payload: ApiTokenCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    token_str = uuid.uuid4().hex
    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
    api_token = ApiToken(
        token=token_str,
        description=payload.description,
        rate_limit_per_minute=payload.rate_limit_per_minute,
        expires_at=expires_at
    )
    db.add(api_token)
    await db.commit()
    await db.refresh(api_token)
    return {
        'success': True,
        'data': {
            'id': str(api_token.id),
            'token': token_str,
            'description': api_token.description,
            'created_at': api_token.created_at.isoformat()
        }
    }

@router.patch('/{token_id}')
async def update_token(
    token_id: uuid.UUID,
    payload: ApiTokenUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    token = await db.get(ApiToken, token_id)
    if not token:
        from app.core.exceptions import NotFoundError
        raise NotFoundError('Token not found')
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(token, field, value)
    await db.commit()
    await db.refresh(token)
    return {
        'success': True,
        'data': {
            'id': str(token.id),
            'is_active': token.is_active,
            'updated_at': token.updated_at.isoformat()
        }
    }

@router.delete('/{token_id}')
async def delete_token(token_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    token = await db.get(ApiToken, token_id)
    if not token:
        from app.core.exceptions import NotFoundError
        raise NotFoundError('Token not found')
    await db.delete(token)
    await db.commit()
    return {'success': True, 'data': {'message': 'Token deleted'}}
