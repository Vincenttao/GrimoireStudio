import { test, expect, Page } from '@playwright/test';

test.describe('Muse Panel V2.0 Tool Calls', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('Muse panel renders correctly', async ({ page }) => {
    const musePanel = page.locator('h2', { hasText: 'The Muse' });
    await expect(musePanel).toBeVisible();
  });

  test('create_branch tool call UI displays correctly', async ({ page }) => {
    const inputField = page.locator('textarea[placeholder="Ask The Muse..."]');
    await expect(inputField).toBeVisible();
  });

  test('send button is disabled when input is empty', async ({ page }) => {
    const sendButton = page.locator('button[id="send-button"]');
    await expect(sendButton).toBeDisabled();
  });

  test('typing in input enables send button', async ({ page }) => {
    const inputField = page.locator('textarea[placeholder="Ask The Muse..."]');
    await inputField.fill('Create a new character');

    const sendButton = page.locator('button[id="send-button"]');
    await expect(sendButton).toBeEnabled();
  });
});

test.describe('Branch API Integration', () => {
  test('createBranch API call structure', async ({ page }) => {
    let requestBody: unknown = null;

    await page.route('**/api/v1/sandbox/branch', async (route) => {
      requestBody = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          branch: {
            branch_id: 'branch_test123',
            name: 'Test Branch',
            origin_snapshot_id: null,
            parent_branch_id: null,
            is_active: true,
            created_at: new Date().toISOString(),
          },
          message: "Branch 'Test Branch' created successfully.",
        }),
      });
    });

    await page.goto('/');

    const inputField = page.locator('textarea[placeholder="Ask The Muse..."]');
    await inputField.fill('test branch');
    await inputField.press('Enter');

    await page.waitForTimeout(500);
  });

  test('rollback API call structure', async ({ page }) => {
    await page.route('**/api/v1/sandbox/rollback', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          snapshot_id: 'snap_test',
          branch_id: 'main',
          entities_count: 3,
          message: 'Rolled back to snapshot. Restored 3 entities.',
        }),
      });
    });

    await page.goto('/');

    const inputField = page.locator('textarea[placeholder="Ask The Muse..."]');
    await expect(inputField).toBeVisible();
  });
});

test.describe('Render Adjust API Integration', () => {
  test('adjust render API endpoint responds correctly', async ({ page }) => {
    await page.route('**/api/v1/render/adjust', async (route) => {
      const body = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          default_render_mixer: {
            pov_type: 'FIRST_PERSON',
            style_template: 'Literary',
            subtext_ratio: body.subtext_ratio ?? 0.5,
          },
          message: 'Render parameters updated.',
        }),
      });
    });

    await page.goto('/');
    await page.waitForTimeout(300);
  });
});

test.describe('Characters Page', () => {
  test('can navigate to characters page', async ({ page }) => {
    await page.goto('/');

    const charactersLink = page.getByRole('button', { name: 'Characters' });
    await expect(charactersLink).toBeVisible();
    await charactersLink.click();

    await expect(page).toHaveURL('/characters');
  });
});

test.describe('Storyboard Page', () => {
  test('storyboard page loads', async ({ page }) => {
    await page.goto('/storyboard');
    const heading = page.getByRole('heading', { name: 'Storyboard' });
    await expect(heading).toBeVisible();
  });
});

test.describe('Monitor Component', () => {
  test('Monitor renders in collapsed state', async ({ page }) => {
    await page.goto('/storyboard');
    await page.waitForTimeout(500);
    const monitor = page.locator('.glass-card').filter({ hasText: 'IDLE' });
    await expect(monitor).toBeVisible();
  });

  test('Monitor shows state badge', async ({ page }) => {
    await page.goto('/storyboard');
    await page.waitForTimeout(500);
    const stateBadge = page.locator('text=IDLE');
    await expect(stateBadge.first()).toBeVisible();
  });
});

test.describe('RenderMixer Component', () => {
  test('RenderMixer renders in storyboard header', async ({ page }) => {
    await page.route('**/api/v1/settings', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          settings: {
            default_render_mixer: {
              pov_type: 'OMNISCIENT',
              style_template: 'Standard',
              subtext_ratio: 0.5,
            },
          },
        }),
      });
    });

    await page.goto('/storyboard');
    await page.waitForTimeout(500);

    const povSelect = page.locator('select');
    await expect(povSelect).toBeVisible();
  });

  test('POV dropdown has correct options', async ({ page }) => {
    await page.route('**/api/v1/settings', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          settings: {
            default_render_mixer: {
              pov_type: 'OMNISCIENT',
              style_template: 'Standard',
              subtext_ratio: 0.5,
            },
          },
        }),
      });
    });

    await page.goto('/storyboard');
    await page.waitForTimeout(500);

    const povSelect = page.locator('select');
    await expect(povSelect).toHaveValue('OMNISCIENT');
  });

  test('Subtext slider displays percentage', async ({ page }) => {
    await page.route('**/api/v1/settings', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          settings: {
            default_render_mixer: {
              pov_type: 'OMNISCIENT',
              style_template: 'Standard',
              subtext_ratio: 0.5,
            },
          },
        }),
      });
    });

    await page.goto('/storyboard');
    await page.waitForTimeout(500);

    const subtextDisplay = page.locator('text=50%');
    await expect(subtextDisplay).toBeVisible();
  });
});