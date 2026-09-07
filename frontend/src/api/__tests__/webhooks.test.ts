import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { webhooksApi } from '../webhooks';

const server = setupServer(
  http.get('http://localhost:8000/api/v1/webhooks', () => {
    return HttpResponse.json({
      success: true,
      data: [{
        id: 'wh1',
        url: 'https://example.com/hook',
        events: ['tender.ready_for_decision'],
        is_active: true,
        last_sent_at: null,
        last_status: null,
        retry_count: 0,
        created_at: '2026-08-01T00:00:00Z',
      }],
    });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('webhooksApi', () => {
  test('list возвращает вебхуки', async () => {
    const result = await webhooksApi.list();
    expect(result).toHaveLength(1);
    expect(result[0].url).toBe('https://example.com/hook');
  });
});