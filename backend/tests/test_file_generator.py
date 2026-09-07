import pytest
from app.services.file_generator import generate_positions_excel
from app.models.tender_position import TenderPosition
import uuid

@pytest.mark.asyncio
async def test_generate_positions_excel():
    positions = [
        TenderPosition(
            id=uuid.uuid4(),
            tender_id=uuid.uuid4(),
            position_number=1,
            name='Ноутбук',
            characteristics='',
            quantity=10,
            unit='шт',
        )
    ]
    content = await generate_positions_excel(positions)
    assert isinstance(content, bytes)
    assert len(content) > 0
