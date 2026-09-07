import pytest
from app.services.document_parser import extract_text

@pytest.mark.asyncio
async def test_extract_text_txt():
    text = await extract_text('test.txt', b'Hello world', 'text/plain')
    assert text == 'Hello world'

@pytest.mark.asyncio
async def test_extract_text_pdf_stub():
    # Минимальный PDF-заглушка, парсер может вернуть пусто, но не падает
    text = await extract_text('test.pdf', b'%PDF-1.4 fake', 'application/pdf')
    assert text == ''

@pytest.mark.asyncio
async def test_extract_text_unsupported():
    text = await extract_text('test.xyz', b'data', 'application/octet-stream')
    assert text == ''
