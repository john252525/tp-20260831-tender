import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.setting import Setting, SettingHistory
from app.services.settings_service import replace_section_settings, patch_section_settings

@pytest.fixture
def mock_db_session_with_flush():
    session = AsyncMock()
    added_objects = []

    def add_side_effect(obj):
        added_objects.append(obj)

    async def flush_side_effect():
        for obj in added_objects:
            if isinstance(obj, Setting) and obj.id is None:
                obj.id = uuid.uuid4()

    session.add = MagicMock(side_effect=add_side_effect)
    session.flush = AsyncMock(side_effect=flush_side_effect)
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session, added_objects

@pytest.mark.asyncio
async def test_replace_section_writes_history_for_new_key(mock_db_session_with_flush):
    session, added_objects = mock_db_session_with_flush

    # Настраиваем mock: существующих настроек нет
    result_mock = MagicMock()
    result_mock.scalars().all.return_value = []
    session.execute.return_value = result_mock

    data = {'min_total_score': 70}
    await replace_section_settings(session, 'scoring', data)

    assert len(added_objects) == 2
    setting_obj = next(obj for obj in added_objects if isinstance(obj, Setting))
    history_obj = next(obj for obj in added_objects if isinstance(obj, SettingHistory))

    assert setting_obj.section == 'scoring'
    assert setting_obj.key == 'min_total_score'
    assert setting_obj.value == 70
    assert history_obj.setting_id is not None
    assert history_obj.setting_id == setting_obj.id
    assert history_obj.old_value is None
    assert history_obj.new_value == 70

    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_patch_section_adds_new_key(mock_db_session_with_flush):
    session, added_objects = mock_db_session_with_flush

    result_mock = MagicMock()
    result_mock.scalars().all.return_value = []
    session.execute.return_value = result_mock

    data = {'weight_margin': 45}
    await patch_section_settings(session, 'scoring', data)

    assert len(added_objects) == 2
    setting_obj = next(obj for obj in added_objects if isinstance(obj, Setting))
    history_obj = next(obj for obj in added_objects if isinstance(obj, SettingHistory))

    assert setting_obj.key == 'weight_margin'
    assert setting_obj.value == 45
    assert history_obj.old_value is None
    assert history_obj.new_value == 45
    assert history_obj.setting_id == setting_obj.id

    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
