import { useQuery, UseQueryOptions } from '@tanstack/react-query';

export function useApiQuery<T>(
  key: string[],
  fetcher: () => Promise<T>,
  options?: {
    refetchInterval?: number | false | ((query: any) => number | false);
    enabled?: boolean;
    onSuccess?: (data: T) => void;
    onError?: (error: Error) => void;
    staleTime?: number;
    gcTime?: number;
  },
) {
  return useQuery<T>({
    queryKey: key,
    queryFn: fetcher,
    staleTime: options?.staleTime ?? 30_000,
    gcTime: options?.gcTime ?? 5 * 60_000,
    retry: 2,
    refetchOnWindowFocus: false,
    ...options,
  });
}