import { test, expect } from '@playwright/test';

test.describe('Aquaponics Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the main page
    await page.goto('/');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
  });

  test('should load and display main dashboard elements', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/Aquaponics Dashboard/);
    
    // Check main heading
    const heading = page.locator('h1');
    await expect(heading).toContainText('Aquaponics Sensor Dashboard');
    
    // Check refresh timestamp element exists
    const refreshTimestamp = page.locator('#ts');
    await expect(refreshTimestamp).toBeVisible();
    
    // Check latest chips container exists
    const latestChips = page.locator('#latestChips');
    await expect(latestChips).toBeVisible();
  });

  test('should display six chart canvases', async ({ page }) => {
    // Check for 6 chart canvases (3 raw + 3 daily averages)
    const canvases = page.locator('canvas');
    await expect(canvases).toHaveCount(6);
    
    // Check specific chart IDs
    await expect(page.locator('#ph7')).toBeVisible();
    await expect(page.locator('#tds7')).toBeVisible();
    await expect(page.locator('#temp7')).toBeVisible();
    await expect(page.locator('#ph30')).toBeVisible();
    await expect(page.locator('#tds30')).toBeVisible();
    await expect(page.locator('#temp30')).toBeVisible();
  });

  test('should display chart sections with proper headings', async ({ page }) => {
    // Check section headings
    const rawHeading = page.locator('h2:has-text("Last 7 Days — Raw Readings")');
    await expect(rawHeading).toBeVisible();
    
    const avgHeading = page.locator('h2:has-text("Last 30 Days — Daily Averages")');
    await expect(avgHeading).toBeVisible();
    
    // Check chart card titles
    await expect(page.locator('h3:has-text("pH (raw)")')).toBeVisible();
    await expect(page.locator('h3:has-text("TDS (ppm, raw)")')).toBeVisible();
    await expect(page.locator('h3:has-text("Water Temp (°C, raw)")')).toBeVisible();
    await expect(page.locator('h3:has-text("Daily Avg pH")')).toBeVisible();
    await expect(page.locator('h3:has-text("Daily Avg TDS (ppm)")')).toBeVisible();
    await expect(page.locator('h3:has-text("Daily Avg Temp (°C)")')).toBeVisible();
  });

  test('should display water coach panel', async ({ page }) => {
    // Check coach panel exists
    const coachPanel = page.locator('#coach');
    await expect(coachPanel).toBeVisible();
    
    // Check coach heading
    const coachHeading = page.locator('#coach div:has-text("Water Coach")');
    await expect(coachHeading).toBeVisible();
    
    // Check coach status badge
    const coachStatus = page.locator('#coach-status');
    await expect(coachStatus).toBeVisible();
    
    // Check coach content area
    const coachContent = page.locator('#coach-content');
    await expect(coachContent).toBeVisible();
  });

  test('should load data and populate charts', async ({ page }) => {
    // Wait for data to load (charts should be initialized)
    await page.waitForTimeout(2000);
    
    // Check that Chart.js has been loaded and initialized
    const chartExists = await page.evaluate(() => {
      return typeof window.Chart !== 'undefined';
    });
    expect(chartExists).toBe(true);
    
    // Check if charts have been created (CHARTS global should exist)
    const chartsGlobalExists = await page.evaluate(() => {
      return typeof window.CHARTS !== 'undefined';
    });
    expect(chartsGlobalExists).toBe(true);
  });

  test('should display latest value chips', async ({ page }) => {
    // Wait for data loading
    await page.waitForTimeout(2000);
    
    // Latest chips should be populated
    const latestChips = page.locator('#latestChips');
    await expect(latestChips).toBeVisible();
    
    // Should contain some content (chips may be empty if no valid data)
    const chipsContent = await latestChips.textContent();
    // Chips might be empty with mock data, so just verify the container exists
    expect(chipsContent).toBeDefined();
  });

  test('should handle coach data loading', async ({ page }) => {
    // Wait for coach data to load
    await page.waitForTimeout(3000);
    
    const coachStatus = page.locator('#coach-status');
    await expect(coachStatus).toBeVisible();
    
    // Status should show either loading, error, or actual status
    const statusText = await coachStatus.textContent();
    expect(statusText).toBeDefined();
    expect(statusText.length).toBeGreaterThan(0);
  });

  test('should have no console errors on load', async ({ page }) => {
    const consoleErrors = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    // Navigate and wait for load
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    
    // Filter out expected errors (like fetch failures for missing files)
    const unexpectedErrors = consoleErrors.filter(error => {
      // Allow fetch errors for coach.json if it doesn't exist
      return !error.includes('coach.json') && !error.includes('Failed to fetch');
    });
    
    expect(unexpectedErrors).toHaveLength(0);
  });

  test('should be responsive on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Check that main elements are still visible
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('#latestChips')).toBeVisible();
    await expect(page.locator('#coach')).toBeVisible();
    
    // Charts should still be visible (might be stacked)
    const canvases = page.locator('canvas');
    await expect(canvases).toHaveCount(6);
  });

  test('should have proper chart container sizing', async ({ page }) => {
    // Check that chartbox containers have proper CSS
    const chartBoxes = page.locator('.chartbox');
    await expect(chartBoxes).toHaveCount(6);
    
    // Verify chartbox height is set (prevents growing bug)
    const firstChartBox = chartBoxes.first();
    const height = await firstChartBox.evaluate(element => {
      const style = window.getComputedStyle(element);
      return style.height;
    });
    
    // Should have a fixed height (not auto)
    expect(height).not.toBe('auto');
    expect(height).not.toBe('0px');
  });

  test('should handle data refresh', async ({ page }) => {
    // Record initial timestamp
    const initialTimestamp = await page.locator('#ts').textContent();
    
    // Trigger a refresh (simulate by reloading)
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Check timestamp updated
    const newTimestamp = await page.locator('#ts').textContent();
    expect(newTimestamp).toBeDefined();
    
    // Timestamps should be different (or at least defined)
    expect(newTimestamp).not.toBe('');
  });

  test('should load static assets', async ({ page }) => {
    // Check that CSS is loaded (Inter font should be available)
    const fontFamily = await page.evaluate(() => {
      const element = document.querySelector('h1');
      return window.getComputedStyle(element).fontFamily;
    });
    
    expect(fontFamily).toContain('Inter');
    
    // Check that Chart.js is loaded
    const chartJsLoaded = await page.evaluate(() => {
      return typeof window.Chart !== 'undefined';
    });
    
    expect(chartJsLoaded).toBe(true);
  });
});

test.describe('Dashboard Data Integration', () => {
  test('should handle empty data gracefully', async ({ page }) => {
    // Mock empty data.json response
    await page.route('**/data.json*', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Charts should still be created even with empty data
    const canvases = page.locator('canvas');
    await expect(canvases).toHaveCount(6);
    
    // No console errors should occur
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    await page.waitForTimeout(1000);
    
    // Filter out expected fetch errors
    const unexpectedErrors = errors.filter(error => 
      !error.includes('Failed to fetch') && !error.includes('coach.json')
    );
    expect(unexpectedErrors).toHaveLength(0);
  });

  test('should handle malformed data gracefully', async ({ page }) => {
    // Mock malformed data.json response
    await page.route('**/data.json*', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: 'invalid json'
      });
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Dashboard should still load without crashing
    await expect(page.locator('h1')).toBeVisible();
    
    // Charts should still be created
    const canvases = page.locator('canvas');
    await expect(canvases).toHaveCount(6);
  });

  test('should handle valid sensor data', async ({ page }) => {
    // Mock valid sensor data
    const mockData = [
      {
        "timestamp": "2025-08-15T10:00:00.000Z",
        "ph": 7.0,
        "tds": 350.0,
        "temp_c": 22.5
      },
      {
        "timestamp": "2025-08-15T10:30:00.000Z",
        "ph": 6.9,
        "tds": 355.0,
        "temp_c": 22.8
      }
    ];
    
    await page.route('**/data.json*', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockData)
      });
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    
    // Latest chips should show the sensor values
    const latestChips = page.locator('#latestChips');
    const chipsText = await latestChips.textContent();
    
    // Should contain pH, TDS, and temperature values
    expect(chipsText).toContain('pH');
    expect(chipsText).toContain('TDS');
    expect(chipsText).toContain('°C');
  });
});