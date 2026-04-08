import { test, expect } from '@playwright/test';

test.describe('Findings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Findings' }).click();
    await page.waitForLoadState('networkidle');
  });

  test('navigates to /findings and shows heading', async ({ page }) => {
    await expect(page).toHaveURL(/\/findings/);
    await expect(page.getByRole('heading', { name: 'Findings' })).toBeVisible();
  });

  test('priority filter select is rendered', async ({ page }) => {
    const prioritySelect = page.locator('select').first();
    await expect(prioritySelect).toBeVisible();
    await expect(prioritySelect).toHaveValue('');
  });

  test('status filter select is rendered', async ({ page }) => {
    const selects = page.locator('select');
    await expect(selects.nth(1)).toBeVisible();
  });

  test('table header columns are rendered', async ({ page }) => {
    // The table always renders (even with no data the headers are shown)
    // Use locator scoped to thead to avoid ambiguity
    const thead = page.locator('thead');
    await expect(thead.getByText('Priority')).toBeVisible();
    await expect(thead.getByText('Title')).toBeVisible();
    await expect(thead.getByText('Agent')).toBeVisible();
    await expect(thead.getByText('Countries')).toBeVisible();
    await expect(thead.getByText('Status')).toBeVisible();
  });

  test('table element is present in DOM', async ({ page }) => {
    await expect(page.locator('table')).toBeVisible();
  });

  test('table body exists (with or without rows)', async ({ page }) => {
    // tbody is present even when empty — just verify table structure is intact
    const table = page.locator('table');
    await expect(table).toBeVisible();
    // tbody is a child of table — check via count which is 0-safe
    const tbodyCount = await page.locator('tbody').count();
    expect(tbodyCount).toBeGreaterThan(0);
  });

  test('priority filter changes select value', async ({ page }) => {
    const prioritySelect = page.locator('select').first();
    await prioritySelect.selectOption('HIGH');
    await expect(prioritySelect).toHaveValue('HIGH');
    await page.waitForLoadState('networkidle');
    await expect(prioritySelect).toHaveValue('HIGH');
  });

  test('clicking a table row opens the drawer (when data exists)', async ({ page }) => {
    const rows = page.locator('tbody tr');
    const rowCount = await rows.count();

    if (rowCount > 0) {
      await rows.first().click();
      // Drawer: fixed inset-0 z-40 overlay
      await expect(page.locator('.fixed.inset-0')).toBeVisible();
    } else {
      test.skip();
    }
  });

  test('drawer closes when clicking the × button (when data exists)', async ({ page }) => {
    const rows = page.locator('tbody tr');
    const rowCount = await rows.count();

    if (rowCount > 0) {
      await rows.first().click();
      const drawer = page.locator('.fixed.inset-0');
      await expect(drawer).toBeVisible();
      // Click the close × button
      await page.locator('.fixed.inset-0 button.text-2xl').click();
      await expect(drawer).not.toBeVisible();
    } else {
      test.skip();
    }
  });
});
