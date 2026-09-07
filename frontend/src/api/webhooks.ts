import { apiClient, extractData } from './client';

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  last_sent_at: string | null;
  last_status: 'success' | 'error' | null;
  retry_count: number;
  created_at: string;
  secret?: string;
}

export const webhooksApi = {
  async list(): Promise<Webhook[]> {
    const response = await apiClient.get('/webhooks');
    return extractData(response);
  },
  async create(data: {
    url: string;
    events: string[];
    secret?: string;
    is_active?: boolean;
  }): Promise<Webhook> {
    const response = await apiClient.post('/webhooks', data);
    return extractData(response);
  },
  async get(id: string): Promise<Webhook> {
    const response = await apiClient.get(`/webhooks/${id}`);
    return extractData(response);
  },
  async patch(id: string, data: any): Promise<Webhook> {
    const response = await apiClient.patch(`/webhooks/${id}`, data);
    return extractData(response);
  },
  async delete(id: string): Promise<any> {
    const response = await apiClient.delete(`/webhooks/${id}`);
    return extractData(response);
  },
  async test(id: string): Promise<{ delivered: boolean; response_status: number | null; error: string | null }> {
    const response = await apiClient.post(`/webhooks/${id}/test`);
    return extractData(response);
  },
};