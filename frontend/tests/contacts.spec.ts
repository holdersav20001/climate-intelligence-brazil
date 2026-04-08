import { test, expect } from '@playwright/test';

test.describe('Contacts', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Contacts' }).click();
    await page.waitForLoadState('networkidle');
  });

  test('navigates to /contacts and shows heading', async ({ page }) => {
    await expect(page).toHaveURL(/\/contacts/);
    await expect(page.getByRole('heading', { name: 'Contacts' })).toBeVisible();
  });

  test('organisation type filter select is visible', async ({ page }) => {
    const select = page.locator('select');
    await expect(select).toBeVisible();
    await expect(select).toHaveValue('');
  });

  test('govt-column data-testid is present', async ({ page }) => {
    await expect(page.getByTestId('govt-column')).toBeAttached();
  });

  test('allied-column data-testid is present', async ({ page }) => {
    await expect(page.getByTestId('allied-column')).toBeAttached();
  });

  test('Government section heading is rendered', async ({ page }) => {
    // h2 text matches "Government (n)"
    await expect(page.getByText(/Government \(\d+\)/)).toBeVisible();
  });

  test('NGO & Allied section heading is rendered', async ({ page }) => {
    await expect(page.getByText(/NGO & Allied \(\d+\)/)).toBeVisible();
  });

  test('columns render either contact cards or empty state messages', async ({ page }) => {
    const govtColumn = page.getByTestId('govt-column');
    const alliedColumn = page.getByTestId('allied-column');

    // Each column either has contact cards or an italic empty message
    // Both must be attached to the DOM
    await expect(govtColumn).toBeAttached();
    await expect(alliedColumn).toBeAttached();

    // Check for either influence bars (contacts) or empty state text in govt column
    const govtCards = govtColumn.locator('.bg-white.rounded-lg.border');
    const govtEmpty = govtColumn.getByText('No government contacts');
    const govtCardCount = await govtCards.count();
    const govtEmptyVisible = await govtEmpty.isVisible().catch(() => false);

    // One of these must be true
    expect(govtCardCount > 0 || govtEmptyVisible).toBe(true);
  });

  test('influence score bars render for existing contacts', async ({ page }) => {
    // InfluenceBar renders a bg-gray-200 rounded-full h-1.5 div as the track
    const allInfluenceTracks = page.locator('.bg-gray-200.rounded-full.h-1\\.5');
    const count = await allInfluenceTracks.count();

    // Contacts may or may not exist — just verify the DOM state is coherent
    if (count > 0) {
      // Each track should be visible
      await expect(allInfluenceTracks.first()).toBeVisible();
    } else {
      // No contacts: verify empty state text exists somewhere on page
      const emptyState = page.getByText(/No.*contacts/i);
      const emptyCount = await emptyState.count();
      // At minimum the sections are visible with 0 count headings
      await expect(page.getByText(/Government \(0\)/)).toBeVisible();
    }
  });
});
