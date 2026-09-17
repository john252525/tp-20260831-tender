import asyncio
from typing import List, Union
import httpx
from app.core.config import settings

async def generate_embedding(text: str) -> List[float]:
    """Генерирует эмбеддинг через Ollama API (локальный микросервис)."""
    if not settings.embedding_service_url:
        raise RuntimeError('EMBEDDING_SERVICE_URL is not configured')
    url = f'{settings.embedding_service_url.rstrip("/")}/api/embed'
    payload = {
        'model': settings.llm_model_embedding,
        'input': text,
    }
    # Таймаут с запасом на «холодный» старт Ollama (загрузка модели в память),
    # но без длинных серий повторов: если сервис недоступен (например, нехватка
    # памяти), тендер будет возвращён в очередь на повторную обработку.
    timeout = httpx.Timeout(60.0, connect=10.0)
    max_retries = 2
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                # Ollama возвращает {"embeddings": [[...]]}
                embeddings = data.get('embeddings')
                if embeddings and len(embeddings) > 0:
                    return list(embeddings[0])
                # иногда возвращает {"embedding": [...]}
                if 'embedding' in data:
                    return list(data['embedding'])
                raise ValueError('Unexpected Ollama response format')
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 * (attempt + 1))

async def cosine_similarity(vec1: Union[List[float], object], vec2: Union[List[float], object]) -> float:
    """Косинусное сходство между векторами, принимает List или объекты с методом __iter__."""
    try:
        vec1 = list(vec1)
        vec2 = list(vec2)
    except TypeError:
        return 0.0
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)
