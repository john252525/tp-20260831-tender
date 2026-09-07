import { http, HttpResponse } from 'msw';

const API_BASE = 'http://localhost:8000/api/v1';

export const handlers = [
  http.get(`${API_BASE}/health`, () => {
    return HttpResponse.json({ success: true, data: { status: 'healthy' } });
  }),
  http.get(`${API_BASE}/tenders`, () => {
    return HttpResponse.json({
      success: true,
      data: [
        {
          id: '123e4567-e89b-12d3-a456-426614174000',
          source_tender_id: '12345',
          title: 'Поставка ноутбуков HP ProBook',
          description: 'Поставка ноутбуков HP ProBook 450 G10 для нужд учреждения',
          nmck: 1500000.0,
          currency: 'RUB',
          published_at: '2026-08-01T08:00:00Z',
          deadline_at: '2026-08-15T10:00:00Z',
          customer_name: 'ГБУ «Горбольница №1»',
          customer_inn: '7712345678',
          platform: 'ЕИС',
          status: 'RELEVANT',
          score: 78.5,
          matched_category_name: 'Оргтехника',
          similarity_score: 0.87,
          documents_count: 5,
          positions_count: 12,
          suppliers_count: 3,
          best_margin_percent: null,
          has_decision: false,
          created_at: '2026-08-07T10:00:00Z',
          updated_at: '2026-08-07T10:30:00Z',
        },
      ],
      meta: { page: 1, per_page: 20, total: 1, pages: 1 },
    });
  }),
  http.get(`${API_BASE}/tenders/stats`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        total: 12500,
        by_status: { NEW: 150, APPROVED: 45, RELEVANT: 89 },
        by_category: [{ category_id: 'uuid', category_name: 'Оргтехника', count: 340 }],
        avg_processing_time_minutes: 45.3,
        approval_rate_percent: 16.4,
        avg_margin_percent: 22.1,
        total_approved_volume_rub: 15000000,
      },
    });
  }),
  http.get(`${API_BASE}/tasks`, () => {
    return HttpResponse.json({
      success: true,
      data: [
        {
          id: '123e4567-e89b-12d3-a456-426614174001',
          task_type: 'SYNC_TENDERS',
          status: 'IN_PROGRESS',
          progress_percent: 75,
          entity_type: 'tender',
          entity_id: '123e4567-e89b-12d3-a456-426614174000',
          result_summary: null,
          error_message: null,
          created_at: '2026-08-07T11:00:00Z',
          started_at: '2026-08-07T11:00:05Z',
          completed_at: null,
        },
      ],
      meta: { page: 1, per_page: 20, total: 1, pages: 1 },
    });
  }),
  http.get(`${API_BASE}/decisions`, () => {
    return HttpResponse.json({
      success: true,
      data: [
        {
          tender_id: '123e4567-e89b-12d3-a456-426614174000',
          tender_title: 'Поставка ноутбуков',
          nmck: 2500000.0,
          deadline_at: '2026-08-15T10:00:00Z',
          best_supplier: {
            id: 'supplier-1',
            name: 'ООО «Компьютерный мир»',
            offer_id: 'offer-1',
            final_price: 1730000.0,
            margin_percent: 30.8,
          },
          alternative_suppliers: [],
          risk_assessment: { level: 'LOW', factors: [] },
          auto_recommendation: 'APPROVE',
          status: 'READY_FOR_DECISION',
          ready_at: '2026-08-07T12:00:00Z',
        },
      ],
      meta: { page: 1, per_page: 20, total: 1, pages: 1 },
    });
  }),
  http.get(`${API_BASE}/suppliers`, () => {
    return HttpResponse.json({
      success: true,
      data: [
        {
          id: 's1',
          name: 'Поставщик 1',
          email: 's@example.com',
          phone: '+7',
          type: 'distributor',
          tags: [],
          rating: { avg_response_time_hours: 4, response_rate: 0.8 },
          total_lots: 5,
          successful_deals: 2,
          total_volume_rub: 1000000,
          is_active: true,
          created_at: '2026-08-01T00:00:00Z',
        },
      ],
      meta: { page: 1, per_page: 20, total: 1, pages: 1 },
    });
  }),
  http.get(`${API_BASE}/settings/scoring`, () => {
    return HttpResponse.json({
      success: true,
      data: { min_total_score: 60, min_margin_percent: 15, max_risk_level: 'MEDIUM' },
    });
  }),
];