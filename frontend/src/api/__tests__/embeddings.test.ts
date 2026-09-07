import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { embeddingsApi } from '../embeddings';

const server = setupServer(
  http.post('http://localhost:8000/api/v1/embeddings/generate', () => {
    return HttpResponse.json({
      success: true,
      data: { dimensions: 1536, tokens_used: 10, embedding_preview: [0.1, 0.2, 0.3] },
    });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('embeddingsApi', () => {
  test('generate возвращает эмбеддинг', async () => {
    const result = await embeddingsApi.generate({ text: 'тест' });
    expect(result.dimensions).toBe(1536);
  });
});