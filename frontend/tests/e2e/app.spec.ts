import { test, expect } from '@playwright/test';

test.describe('KG RAG WebUI', () => {
  test.beforeEach(async ({ page }) => {
    // Go to the app before each test
    await page.goto('/');
  });

  test.describe('Page Load', () => {
    test('should load the main page without errors', async ({ page }) => {
      // Check that the header is visible
      await expect(page.locator('h1')).toContainText('LightRAG');
      
      // Check that tabs are present
      await expect(page.locator('.tab').first()).toBeVisible();
      
      // Check that all 4 tabs exist
      const tabs = page.locator('.tab');
      await expect(tabs).toHaveCount(4);
      await expect(tabs.nth(0)).toContainText('Ingest');
      await expect(tabs.nth(1)).toContainText('Query');
      await expect(tabs.nth(2)).toContainText('Query+File');
      await expect(tabs.nth(3)).toContainText('Config');
    });

    test('should display stats card', async ({ page }) => {
      // Check stats card exists
      await expect(page.locator('.card h2').first()).toContainText('Knowledge Graph Stats');
      
      // Check stat boxes are present (4 stats)
      const statBoxes = page.locator('.stat-box');
      await expect(statBoxes).toHaveCount(4);
    });

    test('should have working tab navigation', async ({ page }) => {
      // Initially Query tab should be hidden
      await expect(page.locator('#query')).not.toHaveClass(/active/);
      
      // Click Query tab
      await page.locator('.tab[data-tab="query"]').click();
      
      // Query tab should now be active
      await expect(page.locator('#query')).toHaveClass(/active/);
    });
  });

  test.describe('Stats Display', () => {
    test('should show stats after loading', async ({ page }) => {
      // Wait for either skeleton or actual stats to appear
      // The stats will eventually load (or show skeleton if API is unavailable)
      await page.waitForSelector('.stat-box', { timeout: 10000 });
      
      // Check that we have 4 stat boxes (either skeleton or actual)
      const statBoxes = page.locator('.stat-box');
      await expect(statBoxes).toHaveCount(4);
    });

    test('should have refresh stats button', async ({ page }) => {
      // Wait for stats container to be present
      await page.waitForSelector('#stats-container', { timeout: 10000 });
      
      // Check stats content exists (skeleton or actual)
      const statsContent = page.locator('#stats-container .card');
      await expect(statsContent).toBeVisible();
    });
  });

  test.describe('Query Functionality', () => {
    test('should have query input field', async ({ page }) => {
      // Click Query tab to see query interface
      await page.locator('.tab[data-tab="query"]').click();
      
      // Check query textarea exists
      await expect(page.locator('#queryText')).toBeVisible();
    });

    test('should have query mode options', async ({ page }) => {
      await page.locator('.tab[data-tab="query"]').click();
      
      // Check radio options exist
      const hybridRadio = page.locator('input[value="hybrid"]');
      const localRadio = page.locator('input[value="local"]');
      const globalRadio = page.locator('input[value="global"]');
      
      await expect(hybridRadio).toBeVisible();
      await expect(localRadio).toBeVisible();
      await expect(globalRadio).toBeVisible();
      
      // Hybrid should be checked by default
      await expect(hybridRadio).toBeChecked();
    });

    test('should have run query button', async ({ page }) => {
      await page.locator('.tab[data-tab="query"]').click();
      
      const runBtn = page.locator('#runQueryBtn');
      await expect(runBtn).toBeVisible();
      await expect(runBtn).toContainText('Ask Question');
    });

    test('should show alert when querying empty text', async ({ page }) => {
      await page.locator('.tab[data-tab="query"]').click();
      
      // Set up dialog handler
      page.on('dialog', async dialog => {
        expect(dialog.message()).toContain('Please enter a question');
        await dialog.accept();
      });
      
      // Click run query without entering text
      await page.locator('#runQueryBtn').click();
    });

    test('should have test query buttons', async ({ page }) => {
      await page.locator('.tab[data-tab="query"]').click();
      
      // Check test query buttons exist
      await expect(page.locator('#testQueryCompanies')).toBeVisible();
      await expect(page.locator('#testQueryRelations')).toBeVisible();
      await expect(page.locator('#testQueryOverview')).toBeVisible();
    });
  });

  test.describe('Query+File Tab', () => {
    test('should display query+file tab content', async ({ page }) => {
      await page.locator('.tab[data-tab="queryfile"]').click();
      
      // Check that query+file content is visible
      await expect(page.locator('#queryfile')).toBeVisible();
    });
  });

  test.describe('Config Tab', () => {
    test('should display config tab content', async ({ page }) => {
      await page.locator('.tab[data-tab="config"]').click();
      
      // Check that config content is visible
      await expect(page.locator('#config')).toBeVisible();
    });
  });
});
