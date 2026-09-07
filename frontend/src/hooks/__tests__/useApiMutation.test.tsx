import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useApiMutation } from '../useApiMutation';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { apiClient } from '../../api/client';

const server = setupServer(
  http.post('http://localhost:8000/api/v1/test', () => {
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

describe('useApiMutation', () => {
  test('вызывает мутацию и возвращает данные', async () => {
    const { result } = renderHook(
      () => useApiMutation((data: any) => apiClient.post('/test', data).then((r) => r.data.data)),
      { wrapper }
    );
    act(() => {
      result.current.mutate({ test: true });
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ ok: true });
  });
});