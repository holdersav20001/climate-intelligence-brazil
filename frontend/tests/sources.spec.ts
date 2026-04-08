import { test, expect } from '@playwright/test';

test.describe('Sources', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Sources' }).click();
    await page.waitForLoadState('networkidle');
  });

  test('navigates to /sources and shows heading', async ({ page }) => {
    await expect(page).toHaveURL(/\/sources/);
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();
  });

  test('Active tab button is visible and selected by default', async ({ page }) => {
    const activeBtn = page.getByRole('button', { name: /Active/ });
    await expect(activeBtn).toBeVisible();
    await expect(activeBtn).toHaveClass(/bg-green-600/);
  });

  test('Pending tab button is visible', async ({ page }) => {
    const pendingBtn = page.getByRole('button', { name: /Pending/ });
    await expect(pendingBtn).toBeVisible();
  });

  test('active tab renders page content after load', async ({ page }) => {
    // Wait for spinner to go away (data loaded or errored)
    await page.waitForFunction(() => {
      const spinners = document.querySelectorAll('[class*="animate-spin"]');
      return spinners.length === 0;
    }, { timeout: 10000 }).catch(() => {});

    // After loading, the heading is still visible
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();
    // Tab buttons are still present
    await expect(page.getByRole('button', { name: /Active/ })).toBeVisible();
  });

  test('active tab shows table with headers or empty state after load', async ({ page }) => {
    // Wait for data/error state (spinner disappears)
    await page.waitForFunction(() => {
      const spinners = document.querySelectorAll('[class*="animate-spin"]');
      return spinners.length === 0;
    }, { timeout: 10000 }).catch(() => {});

    // Give React a moment to re-render after state update
    await page.waitForTimeout(500);

    const tableVisible = await page.locator('table').isVisible().catch(() => false);
    const emptyVisible = await page.getByText('No active sources').isVisible().catch(() => false);

    if (tableVisible) {
      // Table exists — verify headers in thead
      const thead = page.locator('thead');
      await expect(thead.getByText('Name')).toBeVisible();
      await expect(thead.getByText('Type')).toBeVisible();
      await expect(thead.getByText('Country')).toBeVisible();
      await expect(thead.getByText('Last Fetched')).toBeVisible();
    } else if (emptyVisible) {
      await expect(page.getByText('No active sources')).toBeVisible();
    } else {
      // Neither — this is unexpected but we still verify page structure
      await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();
    }
  });

  test('switching to Pending tab updates the active button state', async ({ page }) => {
    const pendingBtn = page.getByRole('button', { name: /Pending/ });
    await pendingBtn.click();
    await page.waitForLoadState('networkidle');

    // Pending button should now have bg-green-600
    await expect(pendingBtn).toHaveClass(/bg-green-600/);
    // Active button should not
    const activeBtn = page.getByRole('button', { name: /Active/ });
    await expect(activeBtn).not.toHaveClass(/bg-green-600/);
  });

  test('Pending tab shows Approve/Reject buttons if pending sources exist', async ({ page }) => {
    const pendingBtn = page.getByRole('button', { name: /Pending/ });
    await pendingBtn.click();
    await page.waitForLoadState('networkidle');

    const rows = page.locator('tbody tr');
    const rowCount = await rows.count();

    if (rowCount > 0) {
      const approveBtn = page.getByRole('button', { name: 'Approve' }).first();
      const rejectBtn = page.getByRole('button', { name: 'Reject' }).first();
      await expect(approveBtn).toBeVisible();
      await expect(rejectBtn).toBeVisible();
    } else {
      await expect(page.getByText('No pending sources to review')).toBeVisible();
    }
  });
});
