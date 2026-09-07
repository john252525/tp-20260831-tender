import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test('страница решений отображается', async ({ page }) => {
  await setupApiMocks(page);
  await page.goto('/decisions');
  await expect(page.getByText(/Готово к подтверждению/)).toBeVisible();
});