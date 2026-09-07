import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { decisionsApi } from '../decisions';

const server = setupServer(
  http.get('http://localhost:8000/api/v1/decisions', () => {
    return HttpResponse.json({
      success: true,
      data: [
        {
          tender_id: 't1',
          tender_title: 'Тендер',
          nmck: 1000000,
          deadline_at: '2026-08-15T10:00:00Z',
          best_supplier: { id: 's1', name: 'Поставщик', offer_id: 'o1', final_price: 800000, margin_percent: 20 },
          alternative_suppliers: [],
          risk_assessment: { level: 'LOW', factors: [] },
          auto_recommendation: 'APPROVE',
          status: 'READY_FOR_DECISION',
          ready_at: '2026-08-10T10:00:00Z',
        },
      ],
      meta: { page: 1, per_page: 20, total: 1, pages: 1 },
    });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('decisionsApi', () => {
  test('list возвращает решения', async () => {
    const result = await decisionsApi.list({ page: 1, per_page: 20 });
    expect(result).toHaveLength(1);
    expect(result[0].status).toBe('READY_FOR_DECISION');
  });
});