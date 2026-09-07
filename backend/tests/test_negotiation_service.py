import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.models.tender import Tender
from app.models.lot_supplier import LotSupplier
from app.models.supplier import Supplier
from app.models.commercial_offer import CommercialOffer
from app.models.communication import Communication
from app.models.task import Task
from app.services.negotiation_service import get_negotiation_status

@pytest.mark.asyncio
async def test_get_negotiation_status_real_data():
    tender_id = uuid.uuid4()
    lot_id = uuid.uuid4()
    supplier_id = uuid.uuid4()

    task = Task(
        id=uuid.uuid4(),
        task_type='NEGOTIATE',
        status='COMPLETED',
        entity_type='tender',
        entity_id=tender_id,
        progress_percent=100.0,
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )

    offer_first = CommercialOffer(
        id=uuid.uuid4(),
        lot_supplier_id=lot_id,
        tender_id=tender_id,
        status='FULL',
        margin_percent=20.0,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    offer_last = CommercialOffer(
        id=uuid.uuid4(),
        lot_supplier_id=lot_id,
        tender_id=tender_id,
        status='FULL',
        margin_percent=25.0,
        created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )

    lot = LotSupplier(
        id=lot_id,
        tender_id=tender_id,
        supplier_id=supplier_id,
        status='NEGOTIATING',
        priority=0,
        source='manual',
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    supplier = Supplier(
        id=supplier_id,
        name='ООО Поставщик',
        type='distributor',
        email='supplier@example.com',
    )
    last_comm = Communication(
        id=uuid.uuid4(),
        lot_supplier_id=lot_id,
        tender_id=tender_id,
        direction='outgoing',
        channel='email',
        subject='Уточнение',
        body_text='Просим уточнить',
        message_type='clarification',
        sent_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )

    mock_db = AsyncMock()

    task_result = MagicMock()
    task_result.scalar_one_or_none.return_value = task
    cycles_count = MagicMock()
    cycles_count.scalar_one.return_value = 1
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = [lot]
    offers_result = MagicMock()
    offers_result.scalars().all.return_value = [offer_first, offer_last]
    comm_result = MagicMock()
    comm_result.scalar_one_or_none.return_value = last_comm

    mock_db.execute.side_effect = [
        task_result,
        cycles_count,
        lots_result,
        offers_result,
        comm_result,
    ]

    mock_db.get = AsyncMock(return_value=supplier)

    status_data = await get_negotiation_status(tender_id, mock_db)

    assert status_data['status'] == 'COMPLETED'
    assert status_data['cycles_completed'] == 1
    assert status_data['max_cycles'] == 2
    assert status_data['started_at'] is not None
    assert len(status_data['suppliers']) == 1

    supplier_status = status_data['suppliers'][0]
    assert supplier_status['supplier_id'] == str(supplier_id)
    assert supplier_status['supplier_name'] == 'ООО Поставщик'
    assert supplier_status['initial_margin_percent'] == 20.0
    assert supplier_status['current_margin_percent'] == 25.0
    assert supplier_status['improvement_percent'] == 5.0
    assert supplier_status['last_action'] == 'clarification'
    assert supplier_status['last_action_at'] is not None

@pytest.mark.asyncio
async def test_get_negotiation_status_no_tasks():
    tender_id = uuid.uuid4()
    mock_db = AsyncMock()

    task_result = MagicMock()
    task_result.scalar_one_or_none.return_value = None
    cycles_count = MagicMock()
    cycles_count.scalar_one.return_value = 0
    lots_result = MagicMock()
    lots_result.scalars().all.return_value = []

    mock_db.execute.side_effect = [task_result, cycles_count, lots_result]

    status_data = await get_negotiation_status(tender_id, mock_db)

    assert status_data['status'] == 'IN_PROGRESS'
    assert status_data['cycles_completed'] == 0
    assert status_data['suppliers'] == []
