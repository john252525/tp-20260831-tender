import { apiClient, extractData } from './client';
import type { PaginationMeta, SupplierSearchResults, ConfirmSuppliersResponse, TenderCreateRequest } from './types';

export interface TenderListItem {
  id: string;
  source_tender_id: string;
  title: string;
  description: string;
  nmck: number | null;
  currency: string;
  published_at: string | null;
  deadline_at: string | null;
  customer_name: string;
  customer_inn: string;
  platform: string;
  status: string;
  score: number | null;
  matched_category_name: string | null;
  similarity_score: number | null;
  documents_count: number;
  positions_count: number;
  suppliers_count: number;
  best_margin_percent: number | null;
  has_decision: boolean;
  created_at: string;
  updated_at: string;
}

export interface TenderDetail extends TenderListItem {
  source: { id: string; name: string } | null;
  customer_kpp?: string;
  source_url: string;
  status_history: { status: string; set_at: string }[];
  matched_categories: { id: string; name: string; similarity: number }[];
  score_components: {
    margin_score: number;
    simplicity_score: number;
    volume_score: number;
    competition_score: number;
  } | null;
  structured_data: {
    positions: TenderPosition[];
    requirements: TenderRequirements;
  } | null;
  documents: TenderDocument[];
  suppliers: LotSupplier[];
}

export interface TenderPosition {
  id: string;
  position_number: number;
  name: string;
  characteristics: string;
  gost: string;
  okpd2: string;
  quantity: number;
  unit: string;
  is_essential: boolean;
}

export interface TenderRequirements {
  delivery_date: string | null;
  delivery_address: string;
  delivery_conditions: string;
  license_required: boolean;
  sro_required: boolean;
  security_bid: number | null;
  security_contract: number | null;
  prepayment_percent: number | null;
  stages_count: number;
  special_conditions: string[];
}

export interface TenderDocument {
  id: string;
  filename: string;
  file_size_bytes: number | null;
  mime_type: string;
  source_url: string;
  parse_status: 'PENDING' | 'PARSING' | 'PARSED' | 'ERROR';
  parsed_text_preview: string | null;
}

export interface LotSupplier {
  id: string;
  supplier_id: string;
  supplier_name: string;
  status: string;
  has_cp: boolean;
  cp_margin_percent: number | null;
}

export interface TenderStats {
  total: number;
  by_status: Record<string, number>;
  by_category: { category_id: string; category_name: string; count: number }[];
  avg_processing_time_minutes: number;
  approval_rate_percent: number;
  avg_margin_percent: number;
  total_approved_volume_rub: number;
}

export interface TenderTimelineEvent {
  timestamp: string;
  event_type: 'STATUS_CHANGE' | 'SUPPLIER_ADDED' | 'CP_RECEIVED' | 'NEGOTIATION_STEP' | 'DECISION' | 'ERROR';
  description: string;
  details: any;
}

export const tendersApi = {
  async list(params?: {
    status?: string;
    category_id?: string;
    source_id?: string;
    nmck_min?: number;
    nmck_max?: number;
    published_after?: string;
    published_before?: string;
    deadline_after?: string;
    deadline_before?: string;
    search?: string;
    has_score?: boolean;
    score_min?: number;
    score_max?: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    page?: number;
    per_page?: number;
  }): Promise<{ data: TenderListItem[]; meta: PaginationMeta }> {
    const response = await apiClient.get('/tenders', { params });
    return {
      data: extractData<TenderListItem[]>(response),
      meta: response.data.meta,
    };
  },
  async create(data: TenderCreateRequest): Promise<TenderDetail & { task_id?: string | null }> {
    const response = await apiClient.post('/tenders', data);
    return extractData(response);
  },
  async stats(): Promise<TenderStats> {
    const response = await apiClient.get('/tenders/stats');
    return extractData(response);
  },
  async get(id: string): Promise<TenderDetail> {
    const response = await apiClient.get(`/tenders/${id}`);
    return extractData(response);
  },
  async patch(id: string, data: { status?: string; note?: string }): Promise<TenderDetail> {
    const response = await apiClient.patch(`/tenders/${id}`, data);
    return extractData(response);
  },
  async reprocess(id: string, data: { from_stage: string }): Promise<{ task_id: string }> {
    const response = await apiClient.post(`/tenders/${id}/reprocess`, data);
    return extractData(response);
  },
  async timeline(id: string): Promise<TenderTimelineEvent[]> {
    const response = await apiClient.get(`/tenders/${id}/timeline`);
    return extractData(response);
  },
  async searchSuppliers(id: string, data: {
    max_suppliers?: number;
    channels?: string[];
    priority_order?: string[];
  }): Promise<{ task_id: string }> {
    const response = await apiClient.post(`/tenders/${id}/search-suppliers`, data);
    return extractData(response);
  },
  async getSupplierSearchResults(id: string): Promise<SupplierSearchResults> {
    const response = await apiClient.get(`/tenders/${id}/supplier-search-results`);
    return extractData(response);
  },
  async confirmSuppliers(id: string, data: {
    supplier_ids?: string[];
    new_suppliers?: any[];
  }): Promise<ConfirmSuppliersResponse> {
    const response = await apiClient.post(`/tenders/${id}/supplier-search-results/confirm`, data);
    return extractData(response);
  },
  async requestCP(id: string, data: {
    template_override?: { subject?: string; body?: string };
    attach_positions_table?: boolean;
    supplier_ids?: string[];
  }): Promise<{ task_id: string }> {
    const response = await apiClient.post(`/tenders/${id}/request-cp`, data);
    return extractData(response);
  },
  async getCommunications(id: string): Promise<any> {
    const response = await apiClient.get(`/tenders/${id}/communications`);
    return extractData(response);
  },
  async sendCommunication(id: string, data: {
    supplier_id: string;
    channel: string;
    subject: string;
    body: string;
    message_type?: string;
    attachments_file_ids?: string[];
  }): Promise<any> {
    const response = await apiClient.post(`/tenders/${id}/communications/send`, data);
    return extractData(response);
  },
  async negotiate(id: string, data: {
    action: string;
    target_supplier_ids?: string[];
    custom_instructions?: string;
  }): Promise<{ task_id: string }> {
    const response = await apiClient.post(`/tenders/${id}/negotiate`, data);
    return extractData(response);
  },
  async getNegotiationStatus(id: string): Promise<any> {
    const response = await apiClient.get(`/tenders/${id}/negotiation-status`);
    return extractData(response);
  },
};