import { apiClient, extractData } from './client';

export interface TenderSource {
  id: string;
  name: string;
  type: 'aggregator_api' | 'direct_api';
  api_url: string;
  is_active: boolean;
  last_sync_at: string | null;
  last_sync_status: 'success' | 'error' | null;
  last_error: string | null;
  tenders_synced_total: number;
  config?: {
    rate_limit_rps?: number;
    timeout_seconds?: number;
    retry_count?: number;
    page_size?: number;
  };
  created_at: string;
  updated_at?: string;
}

export const tenderSourcesApi = {
  async list(): Promise<TenderSource[]> {
    const response = await apiClient.get('/tender-sources');
    return extractData(response);
  },
  async create(data: {
    name: string;
    type: string;
    api_url: string;
    api_key: string;
    config?: any;
  }): Promise<TenderSource> {
    const response = await apiClient.post('/tender-sources', data);
    return extractData(response);
  },
  async get(id: string): Promise<TenderSource> {
    const response = await apiClient.get(`/tender-sources/${id}`);
    return extractData(response);
  },
  async put(id: string, data: any): Promise<TenderSource> {
    const response = await apiClient.put(`/tender-sources/${id}`, data);
    return extractData(response);
  },
  async patch(id: string, data: any): Promise<TenderSource> {
    const response = await apiClient.patch(`/tender-sources/${id}`, data);
    return extractData(response);
  },
  async delete(id: string): Promise<any> {
    const response = await apiClient.delete(`/tender-sources/${id}`);
    return extractData(response);
  },
  async sync(id: string, data: { since?: string | null; full_resync?: boolean }): Promise<{ task_id: string }> {
    const response = await apiClient.post(`/tender-sources/${id}/sync`, data);
    return extractData(response);
  },
  async testConnection(id: string): Promise<{ reachable: boolean; latency_ms: number; tenders_available: number | null; error: string | null }> {
    const response = await apiClient.post(`/tender-sources/${id}/test-connection`);
    return extractData(response);
  },
};