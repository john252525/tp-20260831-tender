import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

export function useApiMutation<T, V>(
  mutationFn: (variables: V) => Promise<T>,
  options?: {
    onSuccess?: (data: T, variables: V) => void;
    onError?: (error: Error, variables: V) => void;
    invalidateKeys?: string[][];
    successMessage?: string;
    errorMessage?: string;
  },
) {
  const queryClient = useQueryClient();
  return useMutation<T, Error, V>({
    mutationFn,
    onSuccess: (data, variables) => {
      if (options?.successMessage) {
        toast.success(options.successMessage);
      }
      if (options?.invalidateKeys) {
        options.invalidateKeys.forEach((key) => queryClient.invalidateQueries({ queryKey: key }));
      }
      options?.onSuccess?.(data, variables);
    },
    onError: (error, variables) => {
      const message = options?.errorMessage || error.message || 'Произошла ошибка';
      toast.error(message);
      options?.onError?.(error, variables);
    },
  });
}