import { apiClient, extractData } from './client';

export interface CommercialOfferListItem {
  id: string;
  tender_id: string;
  tender_title: string;
  supplier_id: string;
  supplier_name: string;
  status: 'FULL' | 'PARTIAL' | 'NONE' | 'PROCESSING' | 'ERROR';
  coverage: number;
  total_cost_with_all: number | null;
  margin_absolute: number | null;
  margin_percent: number | null;
  clarification_needed: boolean;
  received_at: string | null;
}

export interface CommercialOfferDetail extends CommercialOfferListItem {
  source_communication_id: string | null;
  clarification_items: string[];
  positions: {
    id: string;
    tender_position_id: string | null;
    tender_position_name: string | null;
    supplier_name: string;
    match_type: 'exact' | 'analog' | 'not_found';
    match_confidence: number | null;
    price_per_unit: number | null;
    quantity_available: number | null;
    delivery_days: number | null;
    nds_included: boolean;
    nds_rate: number | null;
    total_price: number | null;
  }[];
  delivery_terms: {
    delivery_address: string;
    delivery_days: number | null;
    delivery_cost: number | null;
    delivery_conditions: string;
  } | null;
  payment_terms: {
    prepayment_percent: number | null;
    deferred_payment_days: number | null;
    description: string;
  } | null;
  calculated: {
    total_positions_cost: number;
    delivery_cost: number;
    total_cost_with_delivery: number;
    security_bid_cost: number | null;
    security_contract_cost: number | null;
    total_cost_with_all: number;
    nmck: number;
    margin_absolute: number;
    margin_percent: number;
  } | null;
  valid_until: string | null;
  raw_text_snippet: string;
  received_at: string | null;
  parsed_at: string | null;
}

export const commercialOffersApi = {
  async list(params?: {
    tender_id?: string;
    supplier_id?: string;
    status?: string;
    min_margin_percent?: number;
    page?: number;
    per_page?: number;
  }): Promise<CommercialOfferListItem[]> {
    const response = await apiClient.get('/commercial-offers', { params });
    return extractData(response);
  },
  async get(id: string): Promise<CommercialOfferDetail> {
    const response = await apiClient.get(`/commercial-offers/${id}`);
    return extractData(response);
  },
  async reparse(id: string): Promise<{ task_id: string }> {
    const response = await apiClient.post(`/commercial-offers/${id}/reparse`);
    return extractData(response);
  },
};