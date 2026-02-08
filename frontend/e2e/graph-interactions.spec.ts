import { expect, test } from '@playwright/test';

test.describe('Graph3D interaction regression', () => {
  test('supports pin/unpin, camera reset, and gap focus flow', async ({ page }) => {
    await page.goto('/qa/e2e?scenario=knowledge');

    await expect(page.getByTestId('qa-scenario')).toHaveText('knowledge');
    await expect(page.getByTestId('pinned-count')).toHaveText('0');
    await expect(page.getByTestId('selected-gap-id')).toHaveText('none');
    await expect(page.getByTestId('camera-reset-count')).toHaveText('0');

    await page.getByTestId('qa-pin-node').click();
    await expect(page.getByTestId('pinned-count')).toHaveText('1');

    await page.getByTestId('qa-unpin-node').click();
    await expect(page.getByTestId('pinned-count')).toHaveText('0');

    await page.getByTestId('kg-reset-camera').click();
    await expect(page.getByTestId('camera-reset-count')).toHaveText('1');

    await page.getByTestId('gap-card-toggle-gap-1').click();
    await expect(page.getByTestId('selected-gap-id')).toHaveText('gap-1');
  });
});
