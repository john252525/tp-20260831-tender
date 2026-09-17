import asyncio
import random
import time
from typing import List, Dict, Any, Optional
import httpx
import structlog

logger = structlog.get_logger()

# ГосПлан ограничивает частоту запросов и отвечает 429. Держим паузу между
# запросами и делаем несколько попыток с экспоненциальной задержкой.
MIN_REQUEST_INTERVAL_SECONDS = 0.7
MAX_RETRIES = 5
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class GosPlanClient:
    """Клиент для взаимодействия с API ГосПлан (https://v2.gosplan.info) с ретраями."""

    def __init__(self, base_url: str = 'https://v2.gosplan.info'):
        self.base_url = base_url.rstrip('/')
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self.max_retries = MAX_RETRIES
        self._last_request_at = 0.0

    async def _throttle(self):
        """Не допускает слишком частые запросы к API."""
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
            await asyncio.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)
        self._last_request_at = time.monotonic()

    @staticmethod
    def _retry_delay(attempt: int, response: Optional[httpx.Response]) -> float:
        """Задержка перед повтором: Retry-After, иначе экспоненциальная с джиттером."""
        if response is not None:
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    return min(60.0, max(1.0, float(retry_after)))
                except ValueError:
                    pass
        return min(30.0, (2 ** attempt) + random.uniform(0, 1))

    async def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET с троттлингом и ретраями на 429/5xx."""
        for attempt in range(self.max_retries):
            await self._throttle()
            response: Optional[httpx.Response] = None
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                logger.warning('gosplan.http_error', attempt=attempt, status=status, url=url)
                if status not in RETRYABLE_STATUS_CODES or attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self._retry_delay(attempt, exc.response))
            except httpx.RequestError as exc:
                logger.warning('gosplan.request_error', attempt=attempt, url=url, error=str(exc))
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self._retry_delay(attempt, response))

    async def search_purchases(
        self,
        query: Optional[str] = None,
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
        published_forpast: Optional[str] = None,
        sort: Optional[str] = 'published_at_desc',
        region: Optional[int] = None,
        customer_inn: Optional[str] = None,
        limit: int = 20,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """Поиск закупок по параметрам с ретраями."""
        params = {
            'limit': min(limit, 100),
            'skip': skip,
            'sort': sort,
        }
        if published_after is not None:
            params['published_after'] = published_after
        if published_before is not None:
            params['published_before'] = published_before
        if published_forpast is not None:
            params['published_forpast'] = published_forpast
        if query:
            params['object_info'] = query
        if region is not None:
            params['region'] = str(region)
        if customer_inn:
            params['customer'] = customer_inn

        url = f'{self.base_url}/fz44/purchases'
        data = await self._get(url, params=params)
        logger.info('gosplan.purchases.search', count=len(data) if isinstance(data, list) else 0, skip=skip)
        return data

    async def get_purchase(self, purchase_number: str) -> Dict[str, Any]:
        """Получение полной информации о закупке с ретраями."""
        url = f'{self.base_url}/fz44/purchases/{purchase_number}'
        data = await self._get(url)
        logger.info('gosplan.purchase.get', purchase_number=purchase_number)
        return data

    async def get_purchase_documents(self, purchase_number: str) -> List[Dict[str, Any]]:
        """Получение списка документов закупки."""
        purchase = await self.get_purchase(purchase_number)
        docs = purchase.get('docs', [])
        return docs
