import { renderHook, act } from '@testing-library/react';
import { useAuth } from '../useAuth';

describe('useAuth', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('login сохраняет токен и обновляет состояние', () => {
    const { result } = renderHook(() => useAuth());
    act(() => {
      result.current.login('test-token');
    });
    expect(result.current.token).toBe('test-token');
    expect(localStorage.getItem('api_token')).toBe('test-token');
  });

  test('logout удаляет токен', () => {
    localStorage.setItem('api_token', 'test-token');
    const { result } = renderHook(() => useAuth());
    act(() => {
      result.current.logout();
    });
    expect(result.current.token).toBeNull();
    expect(localStorage.getItem('api_token')).toBeNull();
  });
});