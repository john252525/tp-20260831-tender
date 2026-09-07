import { apiClient, extractData } from './client';

export type SettingsSection =
  | 'company'
  | 'scoring'
  | 'communication'
  | 'tender_source'
  | 'ml'
  | 'templates'
  | 'filters';

export interface CompanySettings {
  legal_name: string;
  inn: string;
  kpp: string;
  ogrn: string;
  legal_address: string;
  contact_person: string;
  contact_email: string;
  contact_phone: string;
  email_signature: string;
}

export interface ScoringSettings {
  min_total_score: number;
  min_margin_percent: number;
  max_risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  weight_margin: number;
  weight_simplicity: number;
  weight_volume: number;
  weight_competition: number;
  volume_thresholds?: {
    low: number;
    medium: number;
    high: number;
  };
  volume_scores?: {
    low: number;
    medium: number;
    high: number;
    very_high: number;
  };
  default_competition_score?: number;
  margin_calculation_mode?: string;
  margin_fallback_score?: number;
}

export interface CommunicationSettings {
  max_suppliers_per_lot: number;
  response_timeout_hours: number;
  reminder_after_hours: number;
  max_clarification_cycles: number;
  max_discount_requests_per_supplier: number;
  price_diff_threshold_percent: number;
  channel_priority: string[];
}

export interface FilterSettings {
  min_similarity_accept: number;
  min_similarity_uncertain: number;
  max_tender_age_days: number;
}

export interface SettingsHistoryItem {
  id: string;
  section: string;
  key: string;
  old_value: any;
  new_value: any;
  changed_at: string;
}

export const settingsApi = {
  async getAll(): Promise<Record<SettingsSection, any>> {
    const response = await apiClient.get('/settings');
    return extractData(response);
  },
  async getSection(section: SettingsSection): Promise<any> {
    const response = await apiClient.get(`/settings/${section}`);
    return extractData(response);
  },
  async putSection(section: SettingsSection, data: any): Promise<any> {
    const response = await apiClient.put(`/settings/${section}`, data);
    return extractData(response);
  },
  async patchSection(section: SettingsSection, data: any): Promise<any> {
    const response = await apiClient.patch(`/settings/${section}`, data);
    return extractData(response);
  },
  async getHistory(params?: { page?: number; per_page?: number }): Promise<SettingsHistoryItem[]> {
    const response = await apiClient.get('/settings/history', { params });
    return extractData(response);
  },
};