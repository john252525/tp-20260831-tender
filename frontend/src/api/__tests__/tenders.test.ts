import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { tendersApi } from '../tenders';

const server = setupServer(
  http.get('http://localhost:8000/api/v1/tenders', () => {
    return HttpResponse.json({
      success: true,
      data: [{ id: '123', title: 'Тест' }],
      meta: { page: 1, per_page: 20, total: 1, pages: 1 },
    });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('tendersApi', () => {
  test('list возвращает тендеры', async () => {
    const result = await tendersApi.list({ page: 1, per_page: 20 });
    expect(result.data).toHaveLength(1);
    expect(result.data[0].title).toBe('Тест');
  });
});