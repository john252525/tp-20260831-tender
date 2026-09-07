import { useApiQuery } from './useApiQuery';
import { tasksApi } from '../api/tasks';

export function usePollingTask(taskId: string | null, enabled: boolean) {
  return useApiQuery(
    ['task', taskId || ''],
    () => tasksApi.get(taskId!),
    {
      enabled: enabled && !!taskId,
      refetchInterval: (query) => {
        const status = query.state.data?.status;
        return ['PENDING', 'IN_PROGRESS'].includes(status) ? 3000 : false;
      },
    },
  );
}