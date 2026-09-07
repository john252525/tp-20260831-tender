import { apiClient, extractData } from './client';

export interface DecisionListItem {
  tender_id: string;
  tender_title: string;
  nmck: number;
  deadline_at: string | null;
  best_supplier: {
    id: string;
    name: string;
    offer_id: string;
    final_price: number;
    margin_percent: number;
  };
  alternative_suppliers: {
    id: string;
    name: string;
    margin_percent: number;
  }[];
  risk_assessment: {
    level: 'LOW' | 'MEDIUM' | 'HIGH';
    factors: {
      type: 'price' | 'deadline' | 'compliance' | 'supplier';
      level: 'LOW' | 'MEDIUM' | 'HIGH';
      description: string;
    }[];
  };
  auto_recommendation: 'APPROVE' | 'REVIEW' | 'REJECT';
  status: 'READY_FOR_DECISION' | 'APPROVED' | 'REJECTED' | 'NEEDS_MORE_INFO';
  ready_at: string | null;
}

export const decisionsApi = {
  async list(params?: {
    status?: string;
    risk_level?: string;
    min_margin?: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    page?: number;
    per_page?: number;
  }): Promise<DecisionListItem[]> {
    const response = await apiClient.get('/decisions', { params });
    return extractData(response);
  },
  async approve(tenderId: string, data: {
    chosen_supplier_id: string;
    chosen_offer_id: string;
    comment?: string;
  }): Promise<any> {
    const response = await apiClient.post(`/decisions/${tenderId}/approve`, data);
    return extractData(response);
  },
  async reject(tenderId: string, data: {
    reason: string;
    comment?: string;
  }): Promise<any> {
    const response = await apiClient.post(`/decisions/${tenderId}/reject`, data);
    return extractData(response);
  },
  async requestInfo(tenderId: string, data: {
    instructions: string;
    return_to_stage: string;
  }): Promise<{ task_id: string }> {
    const response = await apiClient.post(`/decisions/${tenderId}/request-info`, data);
    return extractData(response);
  },
};