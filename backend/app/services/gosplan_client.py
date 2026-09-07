import asyncio
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings
import structlog

logger = structlog.get_logger()

class GosPlanClient:
    """Клиент для взаимодействия с API ГосПлан (https://v2.gosplan.info) с ретраями."""

    def __init__(self, base_url: str = 'https://v2.gosplan.info'):
        self.base_url = base_url.rstrip('/')
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self.max_retries = 3

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
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    logger.info('gosplan.purchases.search', count=len(data), skip=skip)
                    return data
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                logger.warning('gosplan.http_error', attempt=attempt, url=url, error=str(exc))
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def get_purchase(self, purchase_number: str) -> Dict[str, Any]:
        """Получение полной информации о закупке с ретраями."""
        url = f'{self.base_url}/fz44/purchases/{purchase_number}'
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()
                    logger.info('gosplan.purchase.get', purchase_number=purchase_number)
                    return data
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                logger.warning('gosplan.http_error', attempt=attempt, url=url, error=str(exc))
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def get_purchase_documents(self, purchase_number: str) -> List[Dict[str, Any]]:
        """Получение списка документов закупки."""
        purchase = await self.get_purchase(purchase_number)
        docs = purchase.get('docs', [])
        return docs
