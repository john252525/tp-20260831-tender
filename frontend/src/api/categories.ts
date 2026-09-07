import { apiClient, extractData } from './client';

export interface Category {
  id: string;
  name: string;
  description: string;
  keywords: string[];
  parent_id: string | null;
  parent_name: string | null;
  children_count?: number;
  is_active: boolean;
  tenders_matched_count?: number;
  embedding_status?: string;
  embedding_dimensions?: number;
  embedding_generated_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CategoryCreateRequest {
  name: string;
  description: string;
  keywords?: string[];
  parent_id?: string | null;
}

export const categoriesApi = {
  async list(params?: {
    search?: string;
    parent_id?: string;
    is_active?: boolean;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    page?: number;
    per_page?: number;
  }): Promise<Category[]> {
    const response = await apiClient.get('/categories', { params });
    return extractData(response);
  },
  async create(data: CategoryCreateRequest): Promise<Category> {
    const response = await apiClient.post('/categories', data);
    return extractData(response);
  },
  async bulkImport(data: { categories: CategoryCreateRequest[] }): Promise<{ task_id: string }> {
    const response = await apiClient.post('/categories/bulk-import', data);
    return extractData(response);
  },
  async get(id: string): Promise<Category> {
    const response = await apiClient.get(`/categories/${id}`);
    return extractData(response);
  },
  async put(id: string, data: CategoryCreateRequest): Promise<Category> {
    const response = await apiClient.put(`/categories/${id}`, data);
    return extractData(response);
  },
  async patch(id: string, data: Partial<CategoryCreateRequest & { is_active?: boolean }>): Promise<Category> {
    const response = await apiClient.patch(`/categories/${id}`, data);
    return extractData(response);
  },
  async delete(id: string): Promise<any> {
    const response = await apiClient.delete(`/categories/${id}`);
    return extractData(response);
  },
  async reEmbed(id: string): Promise<{ task_id: string }> {
    const response = await apiClient.post(`/categories/${id}/re-embed`);
    return extractData(response);
  },
};