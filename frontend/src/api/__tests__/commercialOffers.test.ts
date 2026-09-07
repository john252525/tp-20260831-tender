import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { commercialOffersApi } from '../commercialOffers';

const server = setupServer(
  http.get('http://localhost:8000/api/v1/commercial-offers', () => {
    return HttpResponse.json({
      success: true,
      data: [{
        id: 'co1',
        tender_id: 't1',
        tender_title: 'Тендер',
        supplier_id: 's1',
        supplier_name: 'Поставщик',
        status: 'FULL',
        coverage: 100,
        total_cost_with_all: 900000,
        margin_absolute: 100000,
        margin_percent: 10,
        clarification_needed: false,
        received_at: '2026-08-01T00:00:00Z',
      }],
    });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('commercialOffersApi', () => {
  test('list возвращает КП', async () => {
    const result = await commercialOffersApi.list({ tender_id: 't1' });
    expect(result).toHaveLength(1);
    expect(result[0].status).toBe('FULL');
  });
});