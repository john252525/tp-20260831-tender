import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.tender import Tender
from app.models.tender_requirements import TenderRequirements
from app.models.tender_position import TenderPosition
from app.models.setting import Setting
from app.services.scoring_service import calculate_score

@pytest.fixture
def sample_settings():
    return [
        Setting(section='scoring', key='weight_margin', value=40),
        Setting(section='scoring', key='weight_simplicity', value=30),
        Setting(section='scoring', key='weight_volume', value=20),
        Setting(section='scoring', key='weight_competition', value=10),
        Setting(section='scoring', key='volume_thresholds', value={'low': 100000, 'medium': 1000000, 'high': 5000000}),
        Setting(section='scoring', key='volume_scores', value={'low': 20, 'medium': 50, 'high': 80, 'very_high': 95}),
        Setting(section='scoring', key='default_competition_score', value=50),
        Setting(section='scoring', key='margin_fallback_score', value=50),
    ]

@pytest.mark.asyncio
async def test_calculate_score_basic(sample_settings):
    tender = Tender(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_tender_id='test',
        title='Тест',
        description='',
        nmck=2000000.0,
        status='SCORING',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_db = AsyncMock()
    # Мокаем запрос настроек
    settings_result = MagicMock()
    settings_result.scalars().all.return_value = sample_settings
    # Мокаем запрос позиций (пусто)
    pos_result = MagicMock()
    pos_result.scalars().all.return_value = []
    # Мокаем запрос требований (пусто)
    req_result = MagicMock()
    req_result.scalar_one_or_none.return_value = None
    mock_db.execute.side_effect = [settings_result, pos_result, req_result]

    score, components = await calculate_score(tender, mock_db)
    assert score > 0
    assert 'margin_score' in components
    assert components['volume_score'] == 80  # 2 млн, high threshold 5 млн < 5m => high? Actually 2m <5m so high score 80
    assert components['simplicity_score'] == 100.0
    assert components['competition_score'] == 50.0

@pytest.mark.asyncio
async def test_calculate_score_with_requirements(sample_settings):
    tender = Tender(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_tender_id='test',
        title='Тест',
        description='',
        nmck=500000.0,
        status='SCORING',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    req = TenderRequirements(
        tender_id=tender.id,
        delivery_date=datetime.now(timezone.utc) + timedelta(days=5),
        license_required=False,
        sro_required=False,
        special_conditions=['условие1', 'условие2'],
        stages_count=1,
    )
    positions = [TenderPosition(tender_id=tender.id, position_number=i, name='Позиция', quantity=1) for i in range(12)]
    mock_db = AsyncMock()
    settings_result = MagicMock()
    settings_result.scalars().all.return_value = sample_settings
    pos_result = MagicMock()
    pos_result.scalars().all.return_value = positions
    req_result = MagicMock()
    req_result.scalar_one_or_none.return_value = req
    mock_db.execute.side_effect = [settings_result, pos_result, req_result]

    score, components = await calculate_score(tender, mock_db)
    assert components['simplicity_score'] < 100  # there are deductions
    assert components['volume_score'] == 50  # 500k < 1m
