import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test('страница компании отображается', async ({ page }) => {
  await setupApiMocks(page);
  await page.goto('/settings/company');
  await expect(page.getByText('Реквизиты')).toBeVisible();
});