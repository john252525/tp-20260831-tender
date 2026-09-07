import { apiClient, extractData } from './client';

export interface ApiTokenListItem {
  id: string;
  description: string;
  token_preview: string;
  is_active: boolean;
  rate_limit_per_minute: number;
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface ApiTokenCreated {
  id: string;
  token: string;
  description: string;
  created_at: string;
}

export const tokensApi = {
  async list(): Promise<ApiTokenListItem[]> {
    const response = await apiClient.get('/tokens');
    return extractData<ApiTokenListItem[]>(response);
  },
  async create(data: {
    description: string;
    rate_limit_per_minute?: number;
    expires_in_days?: number | null;
  }): Promise<ApiTokenCreated> {
    const response = await apiClient.post('/tokens', data);
    return extractData<ApiTokenCreated>(response);
  },
  async patch(id: string, data: {
    description?: string;
    is_active?: boolean;
    rate_limit_per_minute?: number;
  }): Promise<any> {
    const response = await apiClient.patch(`/tokens/${id}`, data);
    return extractData(response);
  },
  async delete(id: string): Promise<any> {
    const response = await apiClient.delete(`/tokens/${id}`);
    return extractData(response);
  },
};