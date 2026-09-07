import { useSearchParams } from 'react-router-dom';
import { useCallback } from 'react';

export function useFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const getParam = useCallback(
    (key: string): string | null => searchParams.get(key),
    [searchParams],
  );

  const setParam = useCallback(
    (key: string, value: string | null) => {
      const newParams = new URLSearchParams(searchParams);
      if (value === null || value === '' || value === undefined) {
        newParams.delete(key);
      } else {
        newParams.set(key, value);
      }
      setSearchParams(newParams, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const resetAll = useCallback(() => {
    setSearchParams({}, { replace: true });
  }, [setSearchParams]);

  return { searchParams, getParam, setParam, resetAll };
}