import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.commercial_offer import CommercialOffer, OfferPosition
from app.models.tender_position import TenderPosition
from app.models.tender import Tender
from app.models.tender_requirements import TenderRequirements
from app.services.cp_parser import parse_cp

@pytest.mark.asyncio
async def test_parse_cp_success():
    offer_id = uuid.uuid4()
    tender_id = uuid.uuid4()
    position_id = uuid.uuid4()

    offer = CommercialOffer(
        id=offer_id,
        lot_supplier_id=uuid.uuid4(),
        tender_id=tender_id,
        status='PROCESSING',
        coverage=0.0,
        raw_text_snippet='Ноутбук HP ProBook - 85000 руб за шт, доставка 5000',
    )
    tender_position = TenderPosition(
        id=position_id,
        tender_id=tender_id,
        position_number=1,
        name='Ноутбук HP ProBook',
        characteristics='',
        quantity=10,
        unit='шт',
    )
    requirements = TenderRequirements(
        tender_id=tender_id,
        security_bid=10000,
        security_contract=50000,
    )
    tender = Tender(
        id=tender_id,
        source_id=uuid.uuid4(),
        source_tender_id='test',
        title='Поставка ноутбуков',
        nmck=1000000.0,
    )

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(side_effect=[offer, tender])

    # Результаты для select TenderPosition
    positions_result = MagicMock()
    positions_result.scalars().all.return_value = [tender_position]

    # Результаты для select TenderRequirements
    requirements_result = MagicMock()
    requirements_result.scalar_one_or_none.return_value = requirements

    # Результат для delete OfferPosition (не используется, но нужен для side_effect)
    delete_result = MagicMock()

    # side_effect: первый вызов - positions, второй - requirements, третий - delete
    mock_db.execute.side_effect = [
        positions_result,
        requirements_result,
        delete_result,
    ]

    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    with patch('app.services.cp_parser._get_client', new_callable=AsyncMock) as mock_client:
        mock_client.return_value = AsyncMock()
        mock_client.return_value.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content='''{
                "positions": [
                    {
                        "tender_position_number": 1,
                        "supplier_name": "Ноутбук HP ProBook",
                        "match_type": "exact",
                        "price_per_unit": 85000,
                        "quantity_available": 20,
                        "delivery_days": 14,
                        "nds_included": true,
                        "nds_rate": 20,
                        "notes": ""
                    }
                ],
                "delivery_terms": {
                    "delivery_address": "",
                    "delivery_days": 14,
                    "delivery_cost": 5000,
                    "delivery_conditions": ""
                },
                "payment_terms": {
                    "prepayment_percent": 30,
                    "deferred_payment_days": 0,
                    "description": ""
                },
                "valid_until": null
            }'''))]
        ))
        result = await parse_cp(offer_id, mock_db)

    assert result is True
    assert offer.status == 'FULL'
    assert offer.coverage == 100.0
    assert offer.total_cost == 850000.0
    assert offer.delivery_cost == 5000.0
    assert offer.margin_percent is not None
