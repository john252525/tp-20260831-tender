import { apiClient, extractData } from './client';
import type { PaginationMeta } from './types';

export interface TaskStatus {
  id: string;
  celery_task_id: string | null;
  task_type: 'SYNC_TENDERS' | 'PROCESS_TENDER' | 'SEARCH_SUPPLIERS' | 'SEND_COMMUNICATIONS' | 'PARSE_CP' | 'NEGOTIATE';
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  progress_percent: number;
  entity_type: string | null;
  entity_id: string | null;
  result_summary: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export const tasksApi = {
  async list(params?: {
    status?: string;
    task_type?: string;
    entity_type?: string;
    entity_id?: string;
    page?: number;
    per_page?: number;
  }): Promise<{ data: TaskStatus[]; meta: PaginationMeta }> {
    const response = await apiClient.get('/tasks', { params });
    return {
      data: extractData<TaskStatus[]>(response),
      meta: response.data.meta,
    };
  },
  async get(id: string): Promise<TaskStatus> {
    const response = await apiClient.get(`/tasks/${id}`);
    return extractData(response);
  },
  async cancel(id: string): Promise<any> {
    const response = await apiClient.post(`/tasks/${id}/cancel`);
    return extractData(response);
  },
};