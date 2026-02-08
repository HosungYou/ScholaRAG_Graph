import { expect, test, type Page } from '@playwright/test';

async function disableMotion(page: Page) {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        transition: none !important;
        animation: none !important;
      }
    `,
  });
}

test.describe('Visual regression snapshots', () => {
  test('GapPanel expanded snapshot', async ({ page }) => {
    await page.goto('/qa/e2e?scenario=gap-panel');
    await disableMotion(page);

    await page.getByTestId('gap-card-toggle-gap-1').click();
    await expect(page.getByTestId('qa-scenario-root')).toHaveScreenshot('gap-panel-expanded.png');
  });

  test('ImportProgress completed snapshot', async ({ page }) => {
    await page.goto('/qa/e2e?scenario=import-completed');
    await disableMotion(page);
    await expect(page.getByTestId('qa-scenario-root')).toHaveScreenshot('import-progress-completed.png');
  });

  test('ImportProgress interrupted snapshot', async ({ page }) => {
    await page.goto('/qa/e2e?scenario=import-interrupted');
    await disableMotion(page);
    await expect(page.getByTestId('qa-scenario-root')).toHaveScreenshot('import-progress-interrupted.png');
  });

  test('Graph3D shell snapshot', async ({ page }) => {
    await page.goto('/qa/e2e?scenario=graph3d');
    await disableMotion(page);
    await expect(page.getByTestId('qa-scenario-root')).toHaveScreenshot('graph3d-shell.png');
  });

  test('KnowledgeGraph3D shell snapshot', async ({ page }) => {
    await page.goto('/qa/e2e?scenario=knowledge');
    await disableMotion(page);
    await expect(page.getByTestId('qa-scenario-root')).toHaveScreenshot('knowledge-graph3d-shell.png');
  });
});
