import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test('список тендеров отображается', async ({ page }) => {
  await setupApiMocks(page);
  await page.goto('/tenders');
  await expect(page.getByText(/Всего:/)).toBeVisible();
  await expect(page.getByText('Экспорт CSV')).toBeVisible();
});

test('открытие карточки тендера', async ({ page }) => {
  await setupApiMocks(page);
  await page.goto('/tenders');
  const firstTenderLink = page.locator('table tbody tr td button').first();
  if (await firstTenderLink.count()) {
    await firstTenderLink.click();
    await expect(page).toHaveURL(/\/tenders\//);
  }
});