import { expect, test } from '@playwright/test';
import { login, selectTab } from './helpers';

test.describe('wizard and workspace', () => {
  test('guided wizard creates a contract and opens the workspace', async ({ page }) => {
    await login(page);

    await page.goto('/contracts/new');
    await expect(page.getByRole('heading', { level: 1, name: 'New contract' })).toBeVisible();
    await page.getByRole('button', { name: 'Continue' }).click();

    const name = `E2E wizard ${Date.now()}`;
    await page.getByLabel('Contract name').fill(name);
    await page.getByLabel('Contract type').selectOption('service_agreement');
    await page.getByLabel('Jurisdiction').selectOption('MA');
    await page.getByRole('button', { name: 'Create contract' }).click();

    await page.waitForURL(/\/contracts\/\d+/);
    await expect(page.getByRole('tablist', { name: 'Contract workspace sections' })).toBeVisible();
    await expect(page.getByRole('heading', { level: 1, name })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Generate draft' })).toBeVisible();
  });

  test('workspace tabs support keyboard navigation and validation runs', async ({ page }) => {
    await login(page);
    await page.goto('/contracts/new');
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByLabel('Contract name').fill(`E2E tabs ${Date.now()}`);
    await page.getByRole('button', { name: 'Create contract' }).click();
    await page.waitForURL(/\/contracts\/\d+/);

    const sectionsTab = page.getByRole('tab', { name: 'Sections' });
    await sectionsTab.click();
    await page.keyboard.press('ArrowRight');
    const validationTab = page.getByRole('tab', { name: 'Validation' });
    await expect(validationTab).toHaveAttribute('aria-selected', 'true');

    await page.getByRole('button', { name: 'Run validation' }).click();
    await expect(page.getByText(/No open blockers|blocker/).first()).toBeVisible();

    await selectTab(page, 'Versions');
    await expect(
      page.getByText('The API exposes version numbers, flags, and timestamps'),
    ).toBeVisible();

    await selectTab(page, 'Approvals');
    await expect(page.getByRole('heading', { name: 'Human approval' })).toBeVisible();

    await selectTab(page, 'Export');
    await expect(page.getByRole('heading', { name: 'Export' })).toBeVisible();

    await selectTab(page, 'Risks');
    await expect(page.getByRole('button', { name: 'Run risk analysis' })).toBeVisible();

    await selectTab(page, 'Negotiation');
    await expect(page.getByRole('heading', { name: 'New negotiation item' })).toBeVisible();

    await selectTab(page, 'Audit');
    await expect(page.getByRole('heading', { name: 'Audit trail' })).toBeVisible();
  });

  test('section evidence opens directly in the sections tab', async ({ page }) => {
    await login(page);
    await page.goto('/contracts/new');
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByLabel('Contract name').fill(`E2E evidence ${Date.now()}`);
    await page.getByRole('button', { name: 'Create contract' }).click();
    await page.waitForURL(/\/contracts\/\d+/);

    const evidenceButton = page.getByRole('button', { name: /^Evidence \(/ }).first();
    await expect(evidenceButton).toBeVisible();
    await evidenceButton.click();
    await expect(page.getByRole('button', { name: 'Hide evidence' }).first()).toBeVisible();
    await expect(
      page.getByText(/Evidence for|No approved evidence for this section/).first(),
    ).toBeVisible();
  });
});
