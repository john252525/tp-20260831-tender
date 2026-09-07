import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test('вход с токеном', async ({ page }) => {
  await setupApiMocks(page);
  await page.goto('/auth');
  await page.getByPlaceholder('Введите токен').fill('test-token');
  await page.getByRole('button', { name: 'Войти' }).click();
  await expect(page).toHaveURL('/');
});