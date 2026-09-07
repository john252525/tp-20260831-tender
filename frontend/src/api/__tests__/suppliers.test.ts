import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { suppliersApi } from '../suppliers';

const server = setupServer(
  http.get('http://localhost:8000/api/v1/suppliers', () => {
    return HttpResponse.json({
      success: true,
      data: [
        {
          id: 's1',
          name: 'Поставщик 1',
          email: 's@example.com',
          phone: '+7',
          type: 'distributor',
          tags: [],
          rating: { avg_response_time_hours: 4, response_rate: 0.8 },
          total_lots: 5,
          successful_deals: 2,
          total_volume_rub: 1000000,
          is_active: true,
          created_at: '2026-08-01T00:00:00Z',
        },
      ],
      meta: { page: 1, per_page: 20, total: 1, pages: 1 },
    });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('suppliersApi', () => {
  test('list возвращает поставщиков', async () => {
    const result = await suppliersApi.list({ page: 1, per_page: 20 });
    expect(result.data).toHaveLength(1);
    expect(result.data[0].name).toBe('Поставщик 1');
  });
});