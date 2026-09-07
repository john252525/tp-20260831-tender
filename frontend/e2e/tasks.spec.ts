import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test('страница задач отображается', async ({ page }) => {
  await setupApiMocks(page);
  await page.goto('/tasks');
  await expect(page.getByText('Асинхронные операции системы')).toBeVisible();
});