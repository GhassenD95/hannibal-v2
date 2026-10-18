import { expect, test } from '@playwright/test';
import { login } from './helpers';

test.describe('design system stories', () => {
  test('shows component states across story tabs', async ({ page }) => {
    await login(page);
    await page.goto('/stories');
    await expect(page.getByRole('heading', { level: 1, name: 'Component stories' })).toBeVisible();

    await page.getByRole('tab', { name: 'Badges' }).click();
    await expect(page.getByText('Status colors are always paired with a text label')).toBeVisible();

    await page.getByRole('tab', { name: 'Alerts' }).click();
    await expect(page.getByText('Export blocked')).toBeVisible();

    await page.getByRole('tab', { name: 'States' }).click();
    await expect(page.getByText('Loading contract workspace…')).toBeVisible();
    await expect(page.getByText('No negotiation items')).toBeVisible();
    await expect(page.getByText('Cannot reach the Hannibal API')).toBeVisible();

    await page.getByRole('tab', { name: 'Forms' }).click();
    await expect(page.getByText('Enter a numeric amount greater than zero.')).toBeVisible();
  });
});
