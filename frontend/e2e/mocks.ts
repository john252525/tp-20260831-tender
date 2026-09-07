import { Page } from '@playwright/test';

export async function setupApiMocks(page: Page) {
  // Health
  await page.route('**/api/v1/health', (route) => {
    return route.fulfill({ json: { success: true, data: { status: 'healthy' } } });
  });

  // Tenders
  await page.route('**/api/v1/tenders**', (route) => {
    const url = route.request().url();
    if (url.includes('/stats')) {
      return route.fulfill({
        json: {
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
        },
      });
    }
    if (url.includes('/tenders/')) {
      return route.fulfill({
        json: {
          success: true,
          data: {
            id: '123e4567-e89b-12d3-a456-426614174000',
            source: { id: 'src1', name: 'Источник' },
            source_tender_id: '12345',
            title: 'Поставка ноутбуков HP ProBook',
            description: 'Поставка ноутбуков HP ProBook 450 G10',
            nmck: 1500000.0,
            currency: 'RUB',
            published_at: '2026-08-01T08:00:00Z',
            deadline_at: '2026-08-15T10:00:00Z',
            customer: { name: 'ГБУ «Горбольница №1»', inn: '7712345678', kpp: '771201001' },
            platform: 'ЕИС',
            source_url: 'https://example.com',
            status: 'RELEVANT',
            status_history: [],
            matched_categories: [],
            score: 78.5,
            score_components: { margin_score: 85, simplicity_score: 70, volume_score: 90, competition_score: 50 },
            structured_data: { positions: [], requirements: {} },
            documents: [],
            suppliers: [],
            created_at: '2026-08-07T10:00:00Z',
            updated_at: '2026-08-07T10:30:00Z',
          },
        },
      });
    }
    return route.fulfill({
      json: {
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
      },
    });
  });

  // Tasks
  await page.route('**/api/v1/tasks**', (route) => {
    return route.fulfill({
      json: {
        success: true,
        data: [
          {
            id: 'task1',
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
      },
    });
  });

  // Decisions
  await page.route('**/api/v1/decisions**', (route) => {
    return route.fulfill({
      json: {
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
      },
    });
  });

  // Suppliers
  await page.route('**/api/v1/suppliers**', (route) => {
    return route.fulfill({
      json: {
        success: true,
        data: [
          {
            id: 's1',
            name: 'Поставщик 1',
            type: 'distributor',
            website: '',
            email: 's@example.com',
            phone: '+7',
            telegram: '',
            inn: '',
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
      },
    });
  });

  // Categories
  await page.route('**/api/v1/categories**', (route) => {
    return route.fulfill({
      json: {
        success: true,
        data: [
          {
            id: 'c1',
            name: 'Категория',
            description: 'Описание',
            keywords: [],
            parent_id: null,
            is_active: true,
            created_at: '2026-08-01T00:00:00Z',
            updated_at: '2026-08-01T00:00:00Z',
          },
        ],
        meta: { page: 1, per_page: 20, total: 1, pages: 1 },
      },
    });
  });

  // Settings: scoring
  await page.route('**/api/v1/settings/scoring', (route) => {
    return route.fulfill({
      json: {
        success: true,
        data: { min_total_score: 60, min_margin_percent: 15, max_risk_level: 'MEDIUM' },
      },
    });
  });

  // Settings: communication
  await page.route('**/api/v1/settings/communication', (route) => {
    return route.fulfill({
      json: {
        success: true,
        data: { max_clarification_cycles: 2, max_discount_requests_per_supplier: 2 },
      },
    });
  });

  // Settings: company
  await page.route('**/api/v1/settings/company', (route) => {
    return route.fulfill({
      json: {
        success: true,
        data: {
          legal_name: 'ООО «Рога и Копыта»',
          inn: '1234567890',
          kpp: '123456789',
          ogrn: '1234567890123',
          legal_address: 'г. Москва',
          contact_person: 'Иван',
          contact_email: 'i@example.com',
          contact_phone: '+7',
          email_signature: 'С уважением',
        },
      },
    });
  });

  // Settings: templates
  await page.route('**/api/v1/settings/templates', (route) => {
    return route.fulfill({
      json: {
        success: true,
        data: {
          cp_request: { subject: 'Запрос КП', body: 'Текст' },
          cp_reminder: { subject: 'Напоминание', body: 'Текст' },
          clarification: { subject: 'Уточнение', body: 'Текст' },
          discount_request: { subject: 'Скидка', body: 'Текст' },
        },
      },
    });
  });

  // Tender sources
  await page.route('**/api/v1/tender-sources', (route) => {
    return route.fulfill({
      json: {
        success: true,
        data: [
          {
            id: 'src1',
            name: 'Источник',
            type: 'aggregator_api',
            api_url: 'https://api.example.com',
            is_active: true,
            last_sync_at: null,
            last_sync_status: null,
            last_error: null,
            tenders_synced_total: 0,
            created_at: '2026-08-01T00:00:00Z',
          },
        ],
      },
    });
  });

  // Commercial offers
  await page.route('**/api/v1/commercial-offers', (route) => {
    return route.fulfill({
      json: {
        success: true,
        data: [
          {
            id: 'co1',
            tender_id: 't1',
            tender_title: 'Тендер',
            supplier_id: 's1',
            supplier_name: 'Поставщик',
            status: 'FULL',
            coverage: 100,
            total_cost_with_all: 900000,
            margin_absolute: 100000,
            margin_percent: 10,
            clarification_needed: false,
            received_at: '2026-08-01T00:00:00Z',
          },
        ],
      },
    });
  });

  // Embeddings
  await page.route('**/api/v1/embeddings/generate', (route) => {
    return route.fulfill({
      json: {
        success: true,
        data: { dimensions: 1536, tokens_used: 10, embedding_preview: [0.1, 0.2, 0.3] },
      },
    });
  });
  await page.route('**/api/v1/embeddings/similarity', (route) => {
    return route.fulfill({
      json: {
        success: true,
        data: { cosine_similarity: 0.9, model: 'test' },
      },
    });
  });

  // Webhooks
  await page.route('**/api/v1/webhooks', (route) => {
    return route.fulfill({
      json: {
        success: true,
        data: [
          {
            id: 'wh1',
            url: 'https://example.com/hook',
            events: ['tender.ready_for_decision'],
            is_active: true,
            last_sent_at: null,
            last_status: null,
            retry_count: 0,
            created_at: '2026-08-01T00:00:00Z',
          },
        ],
      },
    });
  });

  // Tokens
  await page.route('**/api/v1/tokens', (route) => {
    return route.fulfill({
      json: {
        success: true,
        data: [
          {
            id: 'token1',
            description: 'Токен',
            token_preview: 'abc...',
            is_active: true,
            rate_limit_per_minute: 60,
            last_used_at: null,
            expires_at: null,
            created_at: '2026-08-01T00:00:00Z',
          },
        ],
      },
    });
  });

  // Files download
  await page.route('**/api/v1/files/*/download', (route) => {
    return route.fulfill({ body: 'binary', contentType: 'application/octet-stream' });
  });
}