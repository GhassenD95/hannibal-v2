import { expect, test } from '@playwright/test';
import { expectAuthenticatedShell, login } from './helpers';

test.describe('dashboard', () => {
  test('lists contracts with status text, not color alone', async ({ page }) => {
    await login(page);
    await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible();
    await expect(page.getByRole('table')).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Status' })).toBeVisible();

    const firstRow = page.getByRole('rowgroup').nth(1).getByRole('row').first();
    await expect(firstRow).toBeVisible();
    await expect(firstRow.getByRole('link', { name: 'Open' })).toBeVisible();

    await expect(page.getByRole('link', { name: 'New contract' }).first()).toBeVisible();
    await expectAuthenticatedShell(page);
  });

  test('primary navigation reaches admin and evaluation', async ({ page }) => {
    await login(page);
    await page
      .getByRole('navigation', { name: 'Primary' })
      .getByRole('link', { name: 'Admin' })
      .click();
    await expect(page.getByRole('heading', { level: 1, name: /Legal packs/ })).toBeVisible();

    await page
      .getByRole('navigation', { name: 'Primary' })
      .getByRole('link', { name: 'Evaluation' })
      .click();
    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'Deterministic quality gates',
      }),
    ).toBeVisible();
    await expect(page.getByRole('button', { name: 'Run evaluation' })).toBeEnabled();
  });
});
