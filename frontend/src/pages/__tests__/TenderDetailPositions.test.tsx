/**
 * UI-проверка отображения позиций и документов тендера.
 *
 * В качестве ответа API используется реальный снимок ответа стенда
 * (fixtures_tender_detail.json), снятый с работающего бэкенда после
 * синхронизации тендера 0325500000126000243 из ГосПлан.
 *
 * Мокается только сетевой слой (apiClient) — сам компонент страницы,
 * маршрутизация и react-query работают по-настоящему.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import * as fs from 'fs';
import * as path from 'path';

// Читаем снимок реального ответа API напрямую из файла:
// так тест не зависит от особенностей резолва JSON в ts-jest/ESM.
const TenderDetailFixture: any = JSON.parse(
  fs.readFileSync(path.join(__dirname, 'fixtures_tender_detail.json'), 'utf-8'),
);
const fixtureData = TenderDetailFixture.data;
const TENDER_ID = fixtureData.id;

jest.mock('../../api/client', () => {
  const rawFixture = require('fs').readFileSync(
    require('path').join(__dirname, 'fixtures_tender_detail.json'), 'utf-8',
  );
  const fixture = JSON.parse(rawFixture);
  const emptyResponses: Record<string, any> = {
    '/communications': { supplier_threads: [] },
    '/timeline': [],
    '/pipeline-steps': { steps: [], status: null, progress_percent: 0 },
    '/drafts': { drafts: [] },
    '/supplier-search-results': { results: [] },
    '/negotiation-status': { status: 'IN_PROGRESS', suppliers: [] },
  };

  const client = {
    get: jest.fn(async (url: string) => {
      if (url === `/tenders/${fixture.data.id}`) {
        return { data: fixture };
      }
      for (const [suffix, payload] of Object.entries(emptyResponses)) {
        if (url.endsWith(suffix)) {
          return { data: { success: true, data: payload } };
        }
      }
      if (url.startsWith('/commercial-offers')) {
        return { data: { success: true, data: [], meta: { page: 1, per_page: 20, total: 0, pages: 0 } } };
      }
      return { data: { success: true, data: null } };
    }),
    post: jest.fn(async () => ({ data: { success: true, data: {} } })),
    patch: jest.fn(async () => ({ data: { success: true, data: {} } })),
    delete: jest.fn(async () => ({ data: { success: true, data: {} } })),
  };
  return {
    apiClient: client,
    extractData: (response: any) => response.data.data,
    extractError: (error: any) => error?.response?.data?.error || { code: 'UNKNOWN', message: 'err' },
  };
});

// eslint-disable-next-line @typescript-eslint/no-var-requires
const { TenderDetailPage } = require('../TenderDetailPage');

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/tenders/${TENDER_ID}`]}>
        <Routes>
          <Route path="/tenders/:tenderId" element={<TenderDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('TenderDetailPage — позиции и документы (реальный ответ API)', () => {
  test('фикстура содержит реальные данные ГосПлан', () => {
    expect(fixtureData.positions.length).toBeGreaterThan(0);
    expect(fixtureData.documents.length).toBeGreaterThan(0);
    expect(fixtureData.customer_name).toBeTruthy();
    expect(fixtureData.positions[0].okpd2).toMatch(/^\d{2}\.\d{2}/);
  });

  test('вкладка «Позиции» показывает все позиции из API', async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /Позиции/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('tab', { name: /Позиции/i }));

    // Названия/единицы/ОКПД2 в реальных данных могут повторяться
    // (например, несколько позиций одного наименования с разными характеристиками),
    // поэтому проверяем наличие, а не уникальность вхождения.
    for (const position of fixtureData.positions) {
      await waitFor(() => {
        expect(screen.getAllByText(position.name).length).toBeGreaterThan(0);
      });
    }

    const firstPosition = fixtureData.positions[0];
    expect(screen.getAllByText(firstPosition.unit).length).toBeGreaterThan(0);
    expect(screen.getAllByText(firstPosition.okpd2).length).toBeGreaterThan(0);

    // Главная проверка: в таблице ровно столько строк, сколько позиций в API (+1 заголовок)
    const rows = screen.getAllByRole('row');
    expect(rows.length).toBe(fixtureData.positions.length + 1);

    // Каждая позиция из API попала в отдельную строку таблицы
    const tableText = rows.map((row) => row.textContent || '').join('\n');
    for (const position of fixtureData.positions) {
      expect(tableText).toContain(position.characteristics.slice(0, 25));
    }
  });

  test('вкладка «Документы» показывает все файлы закупки', async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /Документы/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('tab', { name: /Документы/i }));

    for (const doc of fixtureData.documents) {
      await waitFor(() => {
        expect(screen.getAllByText(doc.filename).length).toBeGreaterThan(0);
      });
    }
  });

  test('вкладка «Обзор» показывает заказчика и адрес поставки', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(fixtureData.customer_name)).toBeInTheDocument();
    });
    const address = fixtureData.requirements?.delivery_address;
    if (address) {
      expect(screen.getByText(address)).toBeInTheDocument();
    }
  });
});
