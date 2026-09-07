import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { tasksApi } from '../tasks';

const server = setupServer(
  http.get('http://localhost:8000/api/v1/tasks', () => {
    return HttpResponse.json({
      success: true,
      data: [
        {
          id: 't1',
          task_type: 'SYNC_TENDERS',
          status: 'IN_PROGRESS',
          progress_percent: 50,
          entity_type: 'tender',
          entity_id: 'x',
          result_summary: null,
          error_message: null,
          created_at: '2026-08-01T00:00:00Z',
          started_at: null,
          completed_at: null,
        },
      ],
      meta: { page: 1, per_page: 20, total: 1, pages: 1 },
    });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('tasksApi', () => {
  test('list возвращает задачи с meta', async () => {
    const result = await tasksApi.list({ page: 1, per_page: 20 });
    expect(result.data).toHaveLength(1);
    expect(result.meta.total).toBe(1);
  });
});