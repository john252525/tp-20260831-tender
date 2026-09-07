import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { settingsApi } from '../settings';

const server = setupServer(
  http.get('http://localhost:8000/api/v1/settings/scoring', () => {
    return HttpResponse.json({
      success: true,
      data: { min_total_score: 60, min_margin_percent: 15, max_risk_level: 'MEDIUM' },
    });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('settingsApi', () => {
  test('getSection возвращает настройки', async () => {
    const result = await settingsApi.getSection('scoring');
    expect(result.min_total_score).toBe(60);
  });
});