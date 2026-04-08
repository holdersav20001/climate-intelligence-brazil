import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('nav and page heading are visible', async ({ page }) => {
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'World Map' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Findings' })).toBeVisible();
  });

  test('five stat cards render', async ({ page }) => {
    // StatCard renders a label text: Articles, Findings, Contacts, Sources, Reports
    // Use .first() to avoid strict mode violations if text appears multiple times
    await expect(page.getByText('Articles').first()).toBeVisible();
    await expect(page.getByText('Findings').first()).toBeVisible();
    await expect(page.getByText('Contacts').first()).toBeVisible();
    await expect(page.getByText('Sources').first()).toBeVisible();
    await expect(page.getByText('Reports').first()).toBeVisible();
  });

  test('five stat card value elements are present', async ({ page }) => {
    // StatCard value: text-2xl font-bold text-gray-900
    const statValues = page.locator('.text-2xl.font-bold');
    await expect(statValues).toHaveCount(5);
  });

  test('Latest Findings section is present', async ({ page }) => {
    await expect(page.getByText('Latest Findings')).toBeVisible();
  });

  test('Latest Articles section is present', async ({ page }) => {
    await expect(page.getByText('Latest Articles')).toBeVisible();
  });

  test('page renders without crashing (main content area exists)', async ({ page }) => {
    // Verify the main content div is present
    await expect(page.locator('main')).toBeVisible();
    // Stat cards container rendered
    await expect(page.locator('.text-2xl.font-bold').first()).toBeVisible();
  });
});
