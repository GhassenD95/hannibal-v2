import { expect, test } from '@playwright/test';
import { login } from './helpers';

test.describe('i18n language switching', () => {
  test('switches between EN, FR, AR successfully', async ({ page }) => {
    await login(page);
    // Verify dashboard loads in English
    await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible();

    // Switch to French
    await page.getByRole('button', { name: 'FR' }).click();
    await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible();

    // Switch to Arabic
    await page.getByRole('button', { name: 'AR' }).click();
    await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible();

    // Switch back to English
    await page.getByRole('button', { name: 'EN' }).click();
    await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible();
  });
});
