import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { tokensApi } from '../tokens';

const server = setupServer(
  http.get('http://localhost:8000/api/v1/tokens', () => {
    return HttpResponse.json({
      success: true,
      data: [{
        id: 'token1',
        description: 'Токен',
        token_preview: 'abc...',
        is_active: true,
        rate_limit_per_minute: 60,
        last_used_at: null,
        expires_at: null,
        created_at: '2026-08-01T00:00:00Z',
      }],
    });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('tokensApi', () => {
  test('list возвращает токены', async () => {
    const result = await tokensApi.list();
    expect(result).toHaveLength(1);
    expect(result[0].description).toBe('Токен');
  });
});