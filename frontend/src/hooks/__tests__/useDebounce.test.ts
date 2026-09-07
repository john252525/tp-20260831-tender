import { renderHook, act } from '@testing-library/react';
import { useDebounce } from '../useDebounce';

describe('useDebounce', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('возвращает исходное значение сразу', () => {
    const { result } = renderHook(() => useDebounce('test', 300));
    expect(result.current).toBe('test');
  });

  test('обновляет значение после задержки', () => {
    const { result, rerender } = renderHook(({ value }) => useDebounce(value, 300), {
      initialProps: { value: 'one' },
    });

    rerender({ value: 'two' });
    expect(result.current).toBe('one');

    act(() => {
      jest.advanceTimersByTime(300);
    });

    expect(result.current).toBe('two');
  });
});