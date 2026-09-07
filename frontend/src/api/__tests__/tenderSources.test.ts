import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { tenderSourcesApi } from '../tenderSources';

const server = setupServer(
  http.get('http://localhost:8000/api/v1/tender-sources', () => {
    return HttpResponse.json({
      success: true,
      data: [{
        id: 'src1',
        name: 'Источник',
        type: 'aggregator_api',
        api_url: 'https://api.example.com',
        is_active: true,
        last_sync_at: null,
        last_sync_status: null,
        last_error: null,
        tenders_synced_total: 0,
        created_at: '2026-08-01T00:00:00Z',
      }],
    });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('tenderSourcesApi', () => {
  test('list возвращает источники', async () => {
    const result = await tenderSourcesApi.list();
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe('Источник');
  });
});