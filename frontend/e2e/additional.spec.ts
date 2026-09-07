import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test('фильтрация тендеров обновляет URL', async ({ page }) => {
  await setupApiMocks(page);
  await page.goto('/tenders');
  const searchInput = page.getByPlaceholder('Название, описание, заказчик');
  await searchInput.fill('ноутбук');
  await expect(searchInput).toHaveValue('ноутбук');
  await expect.poll(async () => new URL(page.url()).searchParams.get('search')).toBe('ноутбук');
});

test('открытие вкладок карточки тендера', async ({ page }) => {
  await setupApiMocks(page);
  await page.goto('/tenders/123e4567-e89b-12d3-a456-426614174000');
  await expect(page.getByRole('tab', { name: 'Обзор' })).toBeVisible();
  await page.getByRole('tab', { name: /Позиции/ }).click();
  await expect(page.getByRole('tab', { name: /Позиции/ })).toHaveAttribute('aria-selected', 'true');
});

test('страница аналитики отображается', async ({ page }) => {
  await setupApiMocks(page);
  await page.goto('/analytics');
  await expect(page.getByText('Воронка конверсии')).toBeVisible();
});

test('страница эмбеддингов отображается', async ({ page }) => {
  await setupApiMocks(page);
  await page.goto('/debug/embeddings');
  await expect(page.getByText('Генерация')).toBeVisible();
});

test('страница журнала отображается', async ({ page }) => {
  await setupApiMocks(page);
  await page.goto('/debug/logs');
  await expect(page.getByText('Тип события')).toBeVisible();
});

test('страница настроек компании отображается', async ({ page }) => {
  await setupApiMocks(page);
  await page.goto('/settings/company');
  await expect(page.getByText('Реквизиты')).toBeVisible();
});