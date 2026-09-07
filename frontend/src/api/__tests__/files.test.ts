import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { filesApi } from '../files';

const server = setupServer(
  http.get('http://localhost:8000/api/v1/files/:id/download', () => {
    return new HttpResponse('binary', { status: 200 });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('filesApi', () => {
  test('download возвращает blob', async () => {
    const result = await filesApi.download('file1');
    expect(result).toBeInstanceOf(Blob);
  });
});