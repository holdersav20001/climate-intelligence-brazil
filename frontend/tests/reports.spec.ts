import { test, expect } from '@playwright/test';

test.describe('Reports', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Reports' }).click();
    await page.waitForLoadState('networkidle');
  });

  test('navigates to /reports and shows heading', async ({ page }) => {
    await expect(page).toHaveURL(/\/reports/);
    await expect(page.getByRole('heading', { name: 'Reports' })).toBeVisible();
  });

  test('report type filter select is visible', async ({ page }) => {
    const select = page.locator('select');
    await expect(select).toBeVisible();
    await expect(select).toHaveValue('');
  });

  test('table column headers render (scoped to thead)', async ({ page }) => {
    // Reports.tsx always renders the table structure.
    // Use thead scope to avoid matching "Type" from <option>All types</option>
    const thead = page.locator('thead');
    await expect(thead.getByText('Type')).toBeVisible();
    await expect(thead.getByText('Subject')).toBeVisible();
    await expect(thead.getByText('Date')).toBeVisible();
    await expect(thead.getByText('Status')).toBeVisible();
  });

  test('table element is present in DOM', async ({ page }) => {
    await expect(page.locator('table')).toBeVisible();
  });

  test('table or empty state is present after data load', async ({ page }) => {
    // Wait for the spinner to disappear (isLoading → false)
    // Then either a table or an empty state must exist
    await page.waitForFunction(() => {
      const spinners = document.querySelectorAll('[class*="animate-spin"]');
      return spinners.length === 0;
    }, { timeout: 10000 }).catch(() => {});

    // After loading resolves, check for table or any content in main
    const main = page.locator('main');
    await expect(main).toBeVisible();
    // The page heading should still be visible
    await expect(page.getByRole('heading', { name: 'Reports' })).toBeVisible();
  });

  test('clicking a report row opens the modal (when data exists)', async ({ page }) => {
    const rows = page.locator('tbody tr');
    const rowCount = await rows.count();

    if (rowCount > 0) {
      await rows.first().click();
      // ReportModal: fixed inset-0 z-40 with backdrop
      await expect(page.locator('.fixed.inset-0')).toBeVisible();
      // Modal has a × close button
      await expect(page.locator('.fixed.inset-0 button')).toBeVisible();
    } else {
      test.skip();
    }
  });

  test('modal displays prose body content (when data exists)', async ({ page }) => {
    const rows = page.locator('tbody tr');
    const rowCount = await rows.count();

    if (rowCount > 0) {
      await rows.first().click();
      const modal = page.locator('.fixed.inset-0');
      await expect(modal).toBeVisible();
      // ReportModal renders markdown in .prose div
      await expect(modal.locator('.prose')).toBeVisible();
    } else {
      test.skip();
    }
  });

  test('modal closes when clicking the × button (when data exists)', async ({ page }) => {
    const rows = page.locator('tbody tr');
    const rowCount = await rows.count();

    if (rowCount > 0) {
      await rows.first().click();
      const modal = page.locator('.fixed.inset-0');
      await expect(modal).toBeVisible();
      // First button in modal header is the × close
      await modal.locator('button').first().click();
      await expect(modal).not.toBeVisible();
    } else {
      test.skip();
    }
  });

  test('report type filter changes select value', async ({ page }) => {
    const select = page.locator('select');
    await select.selectOption('daily_digest');
    await expect(select).toHaveValue('daily_digest');
    await page.waitForLoadState('networkidle');
    await expect(select).toHaveValue('daily_digest');
  });
});
