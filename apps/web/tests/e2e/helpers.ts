import { expect, type Page } from '@playwright/test';

export const ADMIN_EMAIL = process.env.HANNIBAL_E2E_EMAIL || 'admin@hannibal.local';
export const ADMIN_PASSWORD = process.env.HANNIBAL_E2E_PASSWORD || 'admin123';

export async function login(page: Page, email = ADMIN_EMAIL, password = ADMIN_PASSWORD) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL((url) => !url.pathname.startsWith('/login'));
}

export async function expectAuthenticatedShell(page: Page) {
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();
}

export async function openContract(page: Page, contractId: number) {
  await page.goto(`/contracts/${contractId}`);
  await expect(page.getByRole('tablist', { name: 'Contract workspace sections' })).toBeVisible();
}

export async function selectTab(page: Page, name: string) {
  await page.getByRole('tab', { name }).click();
  await expect(page.getByRole('tab', { name })).toHaveAttribute('aria-selected', 'true');
}
