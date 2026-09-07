import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.models.tender import Tender
from app.models.lot_supplier import LotSupplier
from app.models.supplier import Supplier
from app.models.commercial_offer import CommercialOffer

@pytest.mark.asyncio
async def test_list_decisions_returns_real_data(app_without_auth):
    tender_id = uuid.uuid4()
    best_supplier_id = uuid.uuid4()
    best_offer_id = uuid.uuid4()
    alt_supplier_id = uuid.uuid4()
    alt_offer_id = uuid.uuid4()

    tender = Tender(
        id=tender_id,
        source_id=uuid.uuid4(),
        source_tender_id='stub',
        title='Поставка ноутбуков',
        description='',
        nmck=1000000.0,
        status='READY_FOR_DECISION',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    best_lot = LotSupplier(
        id=uuid.uuid4(),
        tender_id=tender_id,
        supplier_id=best_supplier_id,
        status='FINAL',
        priority=0,
        source='google',
    )
    alt_lot = LotSupplier(
        id=uuid.uuid4(),
        tender_id=tender_id,
        supplier_id=alt_supplier_id,
        status='FINAL',
        priority=1,
        source='internal_db',
    )

    best_offer = CommercialOffer(
        id=best_offer_id,
        lot_supplier_id=best_lot.id,
        tender_id=tender_id,
        status='FULL',
        margin_percent=30.0,
        total_cost_with_all=700000.0,
    )
    alt_offer = CommercialOffer(
        id=alt_offer_id,
        lot_supplier_id=alt_lot.id,
        tender_id=tender_id,
        status='FULL',
        margin_percent=25.0,
        total_cost_with_all=750000.0,
    )

    best_supplier = Supplier(
        id=best_supplier_id,
        name='ООО Лучший',
        type='distributor',
        email='best@example.com',
    )
    alt_supplier = Supplier(
        id=alt_supplier_id,
        name='ООО Альтернативный',
        type='wholesaler',
        email='alt@example.com',
    )

    mock_session = AsyncMock()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    tenders_result = MagicMock()
    tenders_result.scalars().all.return_value = [tender]
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [best_lot, alt_lot]
    alt_offer_result = MagicMock()
    alt_offer_result.scalar_one_or_none.return_value = alt_offer

    mock_session.execute.side_effect = [
        count_result,
        tenders_result,
        lots_result,
        alt_offer_result,
    ]

    mock_session.get = AsyncMock(side_effect=[best_offer, best_supplier, alt_supplier])

    with patch('app.api.v1.decisions.get_auto_recommendation', new_callable=AsyncMock) as mock_rec:
        mock_rec.return_value = {
            'best_supplier_id': str(best_supplier_id),
            'best_offer_id': str(best_offer_id),
            'margin_percent': 30.0,
            'recommendation': 'APPROVE',
            'risk_level': 'LOW',
        }
        with patch('app.api.v1.decisions.calculate_risk', new_callable=AsyncMock) as mock_risk:
            mock_risk.return_value = {'level': 'LOW', 'factors': []}
            with patch('app.api.v1.decisions.get_db') as mock_get_db:
                mock_get_db.return_value = mock_session
                transport = ASGITransport(app=app_without_auth)
                async with AsyncClient(transport=transport, base_url='http://test') as client:
                    response = await client.get('/api/v1/decisions')

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert len(data['data']) == 1
    item = data['data'][0]
    assert item['tender_id'] == str(tender_id)
    assert item['auto_recommendation'] == 'APPROVE'
    assert item['risk_assessment']['level'] == 'LOW'
    assert item['best_supplier']['id'] == str(best_supplier_id)
    assert item['best_supplier']['name'] == 'ООО Лучший'
    assert item['best_supplier']['offer_id'] == str(best_offer_id)
    assert item['best_supplier']['final_price'] == 700000.0
    assert item['best_supplier']['margin_percent'] == 30.0
    assert len(item['alternative_suppliers']) == 1
    alt = item['alternative_suppliers'][0]
    assert alt['id'] == str(alt_supplier_id)
    assert alt['name'] == 'ООО Альтернативный'
    assert alt['margin_percent'] == 25.0
