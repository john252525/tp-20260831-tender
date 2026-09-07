import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { categoriesApi } from '../categories';

const server = setupServer(
  http.get('http://localhost:8000/api/v1/categories', () => {
    return HttpResponse.json({
      success: true,
      data: [{ id: 'c1', name: 'Категория', description: 'Описание', keywords: [], parent_id: null, is_active: true, created_at: '2026-08-01T00:00:00Z', updated_at: '2026-08-01T00:00:00Z' }],
      meta: { page: 1, per_page: 20, total: 1, pages: 1 },
    });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('categoriesApi', () => {
  test('list возвращает категории', async () => {
    const result = await categoriesApi.list({ page: 1, per_page: 20 });
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe('Категория');
  });
});