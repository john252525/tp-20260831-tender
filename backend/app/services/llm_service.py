import asyncio
import json
from typing import Any, Dict, List
import structlog
from openai import AsyncOpenAI
from app.core.config import settings

logger = structlog.get_logger()

async def _get_client() -> AsyncOpenAI:
    if not settings.llm_api_key:
        raise RuntimeError('LLM_API_KEY is not configured')
    return AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base,
    )

async def extract_structured_data(text: str) -> Dict[str, Any]:
    """Извлекает структурированные данные из тендерной документации через LLM с ретраями."""
    prompt = f"""
Ты — анализатор тендерной документации. Извлеки из предоставленного текста структурированные данные.
Текст документации:
{text[:30000]}

Извлеки строго в формате JSON:
1. positions: массив позиций закупки. Для каждой:
   - position_number (int, порядковый номер)
   - name (str, наименование товара/услуги)
   - characteristics (str, все характеристики, если указаны)
   - gost (str, ГОСТ/ТУ если указан, иначе "")
   - okpd2 (str, код ОКПД2 если указан, иначе "")
   - quantity (float, количество)
   - unit (str, единица измерения, по умолчанию "шт")
2. requirements:
   - delivery_date (str в формате YYYY-MM-DD или null)
   - delivery_address (str)
   - delivery_conditions (str)
   - license_required (bool)
   - sro_required (bool)
   - security_bid (float или null, сумма обеспечения заявки)
   - security_contract (float или null, сумма обеспечения контракта)
   - prepayment_percent (float или null)
   - stages_count (int, по умолчанию 1)
   - special_conditions (массив строк)
Если какой-то параметр не указан в тексте — ставь null или значение по умолчанию.
Ответ — ТОЛЬКО JSON, без комментариев.
"""
    client = await _get_client()  # выбрасывает RuntimeError, если ключа нет
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=settings.llm_model_chat,
                messages=[
                    {"role": "system", "content": "Ты — помощник, который извлекает структурированные данные из текста."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            return data
        except Exception as exc:
            logger.warning('llm.extract_structured_data_attempt_failed', attempt=attempt, error=str(exc))
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)

async def classify_incoming_email(subject: str, body_text: str) -> str:
    """Классифицирует входящее письмо. При отсутствии ключа или ошибке возвращает 'other'."""
    prompt = f"""
Классифицируй входящее письмо по его содержанию.
Тема: {subject}
Текст: {body_text[:4000]}
Классификация:
- cp_response: содержит коммерческое предложение, цены, сроки (есть вложение или цены в тексте)
- decline: отказ от участия ("не работаем", "не поставляем", "не наш профиль")
- question: уточняющие вопросы по закупке
- auto_reply: автоответ ("получили", "обрабатывается", "на рассмотрении")
- out_of_office: офис отсутствует, в отпуске
- spam: спам, реклама
- other: не подходит ни под одну категорию
Ответ — ТОЛЬКО одно слово из списка выше.
"""
    try:
        client = await _get_client()
        response = await client.chat.completions.create(
            model=settings.llm_model_chat,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response.choices[0].message.content.strip().lower()
    except Exception as exc:
        logger.error('llm.classify_email_error', error=str(exc))
        return 'other'
