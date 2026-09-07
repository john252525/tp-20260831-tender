from typing import Any
from enum import Enum
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.services.settings_service import (
    get_all_settings, get_section_settings, replace_section_settings,
    patch_section_settings, get_settings_history
)

class SettingsSection(str, Enum):
    company = 'company'
    scoring = 'scoring'
    communication = 'communication'
    tender_source = 'tender_source'
    ml = 'ml'
    templates = 'templates'
    filters = 'filters'

router = APIRouter()

@router.get('')
async def list_settings(db: AsyncSession = Depends(get_db)):
    data = await get_all_settings(db)
    return {'success': True, 'data': data}

@router.get('/history')
async def history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    result = await get_settings_history(db, page, per_page)
    return result

@router.get('/{section}')
async def get_section(section: SettingsSection, db: AsyncSession = Depends(get_db)):
    data = await get_section_settings(db, section.value)
    if data is None:
        raise NotFoundError('Section not found')
    return {'success': True, 'data': data}

@router.put('/{section}')
async def replace_section(section: SettingsSection, payload: dict, db: AsyncSession = Depends(get_db)):
    data = await replace_section_settings(db, section.value, payload)
    return {'success': True, 'data': data}

@router.patch('/{section}')
async def patch_section(section: SettingsSection, payload: dict, db: AsyncSession = Depends(get_db)):
    data = await patch_section_settings(db, section.value, payload)
    return {'success': True, 'data': data}
