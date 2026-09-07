import { apiClient, extractData } from './client';
import type { PaginationMeta, SupplierCreateRequest, SupplierUpdateRequest, MergeSuppliersResponse } from './types';

export interface SupplierListItem {
  id: string;
  name: string;
  type: string;
  website: string;
  email: string;
  phone: string;
  telegram: string;
  inn: string;
  tags: string[];
  rating: {
    avg_response_time_hours: number | null;
    response_rate: number;
  };
  total_lots: number;
  successful_deals: number;
  total_volume_rub: number;
  is_active: boolean;
  created_at: string;
}

export interface SupplierDetail extends SupplierListItem {
  kpp: string;
  ogrn: string;
  legal_address: string;
  contact_persons: { name: string; position: string; email: string; phone: string }[];
  notes: string;
  contacts?: {
    email: string;
    phone: string;
    telegram: string;
    whatsapp: string;
    contact_persons: any[];
  };
  legal_info?: {
    inn: string;
    kpp: string;
    ogrn: string;
    legal_address: string;
  };
  rating?: {
    avg_response_time_hours: number | null;
    response_rate: number;
    price_competitiveness: number;
    reliability: number;
  };
  statistics?: {
    total_lots: number;
    cp_received: number;
    successful_deals: number;
    total_volume_rub: number;
  };
  recent_tenders?: {
    tender_id: string;
    tender_title: string;
    status: string;
    margin_percent: number;
    date: string;
  }[];
  deleted_at: string | null;
  updated_at: string;
}

export const suppliersApi = {
  async list(params?: {
    search?: string;
    type?: string;
    tags?: string;
    has_email?: boolean;
    has_phone?: boolean;
    is_active?: boolean;
    min_successful_deals?: number;
    created_after?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    page?: number;
    per_page?: number;
  }): Promise<{ data: SupplierListItem[]; meta: PaginationMeta }> {
    const response = await apiClient.get('/suppliers', { params });
    return {
      data: extractData<SupplierListItem[]>(response),
      meta: response.data.meta,
    };
  },
  async create(data: SupplierCreateRequest): Promise<SupplierDetail> {
    const response = await apiClient.post('/suppliers', data);
    return extractData(response);
  },
  async merge(data: { primary_id: string; secondary_id: string }): Promise<MergeSuppliersResponse> {
    const response = await apiClient.post('/suppliers/merge', data);
    return extractData(response);
  },
  async get(id: string): Promise<SupplierDetail> {
    const response = await apiClient.get(`/suppliers/${id}`);
    return extractData(response);
  },
  async patch(id: string, data: SupplierUpdateRequest): Promise<SupplierDetail> {
    const response = await apiClient.patch(`/suppliers/${id}`, data);
    return extractData(response);
  },
  async delete(id: string): Promise<any> {
    const response = await apiClient.delete(`/suppliers/${id}`);
    return extractData(response);
  },
  async getCommunications(id: string): Promise<any[]> {
    const response = await apiClient.get(`/suppliers/${id}/communications`);
    return extractData(response);
  },
};