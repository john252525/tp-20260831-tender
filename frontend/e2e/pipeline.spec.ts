import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test('конвейер отображает секции', async ({ page }) => {
  await setupApiMocks(page);
  await page.goto('/');
  await expect(page.getByText(/ВСЕГО/)).toBeVisible();
  await expect(page.getByText('Активные задачи')).toBeVisible();
  await expect(page.getByText('Готовы к решению')).toBeVisible();
  await expect(page.getByText('Последние тендеры')).toBeVisible();
});