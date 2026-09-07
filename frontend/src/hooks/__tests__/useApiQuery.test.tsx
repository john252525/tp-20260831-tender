import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useApiQuery } from '../useApiQuery';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { apiClient } from '../../api/client';

const server = setupServer(
  http.get('http://localhost:8000/api/v1/test', () => {
    return HttpResponse.json({ success: true, data: { ok: true } });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('useApiQuery', () => {
  test('возвращает данные после загрузки', async () => {
    const { result } = renderHook(
      () => useApiQuery(['test'], () => apiClient.get('/test').then((r) => r.data.data)),
      { wrapper }
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ ok: true });
  });
});