import { test, expect } from '@playwright/test';

test.describe('World Map', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'World Map' }).click();
    await page.waitForLoadState('networkidle');
    // Give time slider and map to render (fetches external GeoJSON)
    await page.waitForTimeout(2000);
  });

  test('navigates to /map and shows page heading', async ({ page }) => {
    await expect(page).toHaveURL(/\/map/);
    await expect(page.getByText('Intelligence Map')).toBeVisible();
  });

  test('time slider (range input) is visible', async ({ page }) => {
    const slider = page.locator('input[type="range"]');
    await expect(slider).toBeVisible();
  });

  test('SVG map element is rendered', async ({ page }) => {
    // react-simple-maps renders an <svg> inside the map container
    const svg = page.locator('svg').first();
    await expect(svg).toBeVisible();
  });

  test('map has geographic path elements rendered', async ({ page }) => {
    // ComposableMap renders <path> elements for each country geography
    const paths = page.locator('svg path');
    const count = await paths.count();
    expect(count).toBeGreaterThan(0);
  });

  test('legend text is visible', async ({ page }) => {
    // The legend always renders this hint text
    await expect(page.getByText('Circle size = finding count · Click circle for details')).toBeVisible();
  });

  test('clicking a country marker opens panel (when markers exist)', async ({ page }) => {
    // Markers are <circle> elements inside SVG Marker components.
    // They only appear if findings with matching country codes exist.
    const circles = page.locator('svg circle');
    const circleCount = await circles.count();

    if (circleCount > 0) {
      await circles.first().click();
      // Panel shows "{CC} — {n} findings"
      await expect(page.locator('text=findings').first()).toBeVisible();
      // Close button visible
      await expect(page.locator('button', { hasText: '×' })).toBeVisible();
    } else {
      // No data from backend — just confirm map rendered without error
      await expect(page.locator('svg').first()).toBeVisible();
    }
  });
});
