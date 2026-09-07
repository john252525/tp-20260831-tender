import io
from typing import List, Dict, Any
import openpyxl
from openpyxl.utils import get_column_letter

async def generate_positions_excel(positions: List[Any]) -> bytes:
    """Генерирует Excel-файл с таблицей позиций тендера."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Позиции'

    # Заголовки
    headers = ['№', 'Наименование', 'Характеристики', 'Количество', 'Ед. изм.', 'Цена за ед.', 'Срок поставки']
    ws.append(headers)

    for pos in positions:
        row = [
            pos.position_number,
            pos.name,
            pos.characteristics,
            float(pos.quantity),
            pos.unit,
            '',  # цена пустая
            '',  # срок пустой
        ]
        ws.append(row)

    # Автоширина
    for col_idx, _ in enumerate(headers, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 20

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()
