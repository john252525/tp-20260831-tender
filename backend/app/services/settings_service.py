from typing import Any, Dict, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting, SettingHistory

async def get_all_settings(db: AsyncSession) -> Dict[str, Dict[str, Any]]:
    result = await db.execute(select(Setting))
    settings = result.scalars().all()
    grouped = {}
    for s in settings:
        grouped.setdefault(s.section, {})[s.key] = s.value
    return grouped

async def get_section_settings(db: AsyncSession, section: str) -> Optional[Dict[str, Any]]:
    result = await db.execute(select(Setting).where(Setting.section == section))
    settings = result.scalars().all()
    if not settings:
        return None
    return {s.key: s.value for s in settings}

async def replace_section_settings(db: AsyncSession, section: str, data: Dict[str, Any]) -> Dict[str, Any]:
    existing = (await db.execute(select(Setting).where(Setting.section == section))).scalars().all()
    existing_map = {s.key: s for s in existing}

    new_settings = []
    for key, value in data.items():
        if key in existing_map:
            s = existing_map[key]
            old_value = s.value
            if old_value != value:
                db.add(SettingHistory(
                    setting_id=s.id,
                    section=section,
                    key=key,
                    old_value=old_value,
                    new_value=value
                ))
                s.value = value
        else:
            new_setting = Setting(section=section, key=key, value=value, description='')
            db.add(new_setting)
            new_settings.append((key, value, new_setting))

    await db.flush()
    for key, value, new_setting in new_settings:
        db.add(SettingHistory(
            setting_id=new_setting.id,
            section=section,
            key=key,
            old_value=None,
            new_value=value
        ))

    keys_to_delete = set(existing_map.keys()) - set(data.keys())
    for key in keys_to_delete:
        s = existing_map[key]
        db.add(SettingHistory(
            setting_id=s.id,
            section=section,
            key=key,
            old_value=s.value,
            new_value=None
        ))
        # Исправлено: db.delete синхронный
        db.delete(s)

    await db.commit()
    result = await db.execute(select(Setting).where(Setting.section == section))
    updated = result.scalars().all()
    return {s.key: s.value for s in updated}

async def patch_section_settings(db: AsyncSession, section: str, data: Dict[str, Any]) -> Dict[str, Any]:
    existing = (await db.execute(select(Setting).where(Setting.section == section))).scalars().all()
    existing_map = {s.key: s for s in existing}

    new_settings = []
    for key, value in data.items():
        if key in existing_map:
            s = existing_map[key]
            old_value = s.value
            if old_value != value:
                db.add(SettingHistory(
                    setting_id=s.id,
                    section=section,
                    key=key,
                    old_value=old_value,
                    new_value=value
                ))
                s.value = value
        else:
            new_setting = Setting(section=section, key=key, value=value, description='')
            db.add(new_setting)
            new_settings.append((key, value, new_setting))

    await db.flush()
    for key, value, new_setting in new_settings:
        db.add(SettingHistory(
            setting_id=new_setting.id,
            section=section,
            key=key,
            old_value=None,
            new_value=value
        ))

    await db.commit()
    result = await db.execute(select(Setting).where(Setting.section == section))
    updated = result.scalars().all()
    return {s.key: s.value for s in updated}

async def get_settings_history(db: AsyncSession, page: int, per_page: int) -> dict:
    offset = (page - 1) * per_page
    total = (await db.execute(select(func.count(SettingHistory.id)))).scalar_one()
    result = await db.execute(
        select(SettingHistory).order_by(SettingHistory.changed_at.desc()).offset(offset).limit(per_page)
    )
    items = result.scalars().all()
    data = []
    for h in items:
        data.append({
            'id': str(h.id),
            'section': h.section,
            'key': h.key,
            'old_value': h.old_value,
            'new_value': h.new_value,
            'changed_at': h.changed_at.isoformat()
        })
    pages = (total + per_page - 1) // per_page
    return {
        'success': True,
        'data': data,
        'meta': {'page': page, 'per_page': per_page, 'total': total, 'pages': pages}
    }
