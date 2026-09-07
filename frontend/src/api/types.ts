export interface PaginationMeta {
  page: number;
  per_page: number;
  total: number;
  pages: number;
}

export interface SupplierSearchResults {
  tender_id: string;
  status: 'SUPPLIERS_FOUND' | 'NO_SUPPLIERS_FOUND' | 'SEARCH_IN_PROGRESS';
  searched_at: string | null;
  search_queries_used: string[];
  total_found: number;
  after_dedup: number;
  after_priority_filter: number;
  suppliers: Array<{
    id: string | null;
    name: string;
    type: string;
    website: string;
    email: string;
    phone: string;
    source: 'google' | 'internal_db';
    relevance: 'high' | 'medium' | 'low';
    match_reason: string;
    is_new: boolean;
    already_in_db: boolean;
    selected: boolean;
  }>;
}

export interface ConfirmSuppliersResponse {
  tender_id: string;
  suppliers_linked: number;
  suppliers_created: number;
}

export interface Decision {
  id: string;
  tender_id: string;
  decision: 'APPROVED' | 'REJECTED' | 'NEEDS_MORE_INFO';
  chosen_supplier_id: string | null;
  chosen_offer_id: string | null;
  margin_at_decision: number | null;
  risk_level_at_decision: string | null;
  reason: string;
  decided_at: string;
}

export interface TenderCreateRequest {
  title: string;
  description?: string;
  nmck?: number | null;
  published_at?: string | null;
  deadline_at?: string | null;
  customer_name?: string;
  customer_inn?: string;
  customer_kpp?: string;
  platform?: string;
  source_url?: string;
  documents_urls?: string[];
  skip_auto_processing?: boolean;
}

export interface SupplierCreateRequest {
  name: string;
  type?: 'manufacturer' | 'distributor' | 'wholesaler' | 'retail' | 'unknown';
  website?: string;
  email?: string;
  phone?: string;
  telegram?: string;
  whatsapp?: string;
  inn?: string;
  kpp?: string;
  ogrn?: string;
  legal_address?: string;
  contact_persons?: Array<{
    name: string;
    position?: string;
    email?: string;
    phone?: string;
  }>;
  tags?: string[];
  notes?: string;
}

export interface SupplierUpdateRequest extends Partial<SupplierCreateRequest> {
  is_active?: boolean;
}

export interface MergeSuppliersResponse {
  primary_id: string;
  secondary_id: string;
  merged: boolean;
}