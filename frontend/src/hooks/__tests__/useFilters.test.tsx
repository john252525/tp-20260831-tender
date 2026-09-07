import { renderHook, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { useFilters } from '../useFilters';

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <MemoryRouter initialEntries={['/test?status=NEW']}>{children}</MemoryRouter>
);

describe('useFilters', () => {
  test('getParam возвращает значение', () => {
    const { result } = renderHook(() => useFilters(), { wrapper });
    expect(result.current.getParam('status')).toBe('NEW');
  });

  test('setParam обновляет параметр', () => {
    const { result } = renderHook(() => useFilters(), { wrapper });
    act(() => {
      result.current.setParam('status', 'RELEVANT');
    });
    expect(result.current.getParam('status')).toBe('RELEVANT');
  });

  test('resetAll очищает параметры', () => {
    const { result } = renderHook(() => useFilters(), { wrapper });
    act(() => {
      result.current.resetAll();
    });
    expect(result.current.getParam('status')).toBeNull();
  });
});