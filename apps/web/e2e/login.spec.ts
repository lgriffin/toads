import { expect, test } from '@playwright/test';

// The preview starts signed out: the landing page is the front door and /login is its pretend Discord sign-in.

test('a visitor lands signed out and member pages ask them to log in', async ({ page }) => {
  await page.goto('');
  await expect(page.getByRole('heading', { name: 'Toads', level: 1 })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Members' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Go to your hub' })).toHaveCount(0);

  await page.goto('hub/');
  await expect(page.getByRole('heading', { name: 'Sign in to see this' })).toBeVisible();
  await expect(page.locator('[data-widget]')).toHaveCount(0);
});

test('a raider signs in, sees their own side but not the officer console', async ({ page }) => {
  await page.goto('');
  await page.getByRole('main').getByRole('link', { name: 'Log in with Discord' }).click();
  await expect(page).toHaveURL(/\/toads\/login\/$/);
  await page.getByRole('button', { name: 'Sign in as a raider' }).click();

  await expect(page).toHaveURL(/\/toads\/hub\/$/);
  await expect(page.getByText('Raider', { exact: true })).toBeVisible();
  const members = page.getByRole('navigation', { name: 'Members' });
  await expect(members.getByRole('link')).toHaveText(['Hub', 'Raids & Logs', 'Highlights', 'Bank', 'Me']);
  await expect(page.locator('[data-widget="officer_desk"]')).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Toads badges' })).toHaveCount(0);

  await members.getByRole('link', { name: 'Me' }).click();
  await expect(page.getByRole('region', { name: 'Your badges' })).toBeVisible();

  await page.goto('officers/');
  await expect(page.getByRole('heading', { name: 'Officers only' })).toBeVisible();
});

test('the view switch moves between the raider and officer sides and survives a reload', async ({ page }) => {
  await page.goto('login/');
  await page.getByRole('button', { name: 'Sign in as a raider' }).click();
  await expect(page).toHaveURL(/\/toads\/hub\/$/);

  await page.getByRole('button', { name: 'Switch to officer view' }).click();
  await expect(page.getByText('Officer', { exact: true })).toBeVisible();
  await expect(page.locator('[data-widget="officer_desk"]')).toHaveCount(1);
  await page.getByRole('navigation', { name: 'Members' }).getByRole('link', { name: 'Officers' }).click();
  await expect(page).toHaveURL(/\/toads\/officers\/$/);
  await page.reload();
  await expect(page.getByTestId('application-app-1')).toBeVisible();

  await page.getByRole('button', { name: 'Switch to raider view' }).click();
  await expect(page).toHaveURL(/\/toads\/hub\/$/);
  await expect(page.getByRole('navigation', { name: 'Members' }).getByRole('link', { name: 'Officers' })).toHaveCount(0);
});

test('logging out returns to the public landing page', async ({ page }) => {
  await page.goto('login/');
  await page.getByRole('button', { name: 'Sign in as an officer' }).click();
  await expect(page).toHaveURL(/\/toads\/hub\/$/);
  await page.getByRole('button', { name: 'Log out' }).click();
  await expect(page).toHaveURL(/\/toads\/$/);
  await expect(page.getByRole('main').getByRole('link', { name: 'Log in with Discord' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('navigation', { name: 'Members' })).toHaveCount(0);
});

test('an unknown page is still a 404 for a signed-out visitor', async ({ page }) => {
  await page.goto('does-not-exist/');
  await expect(page.getByRole('heading', { name: 'Not found' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Sign in to see this' })).toHaveCount(0);
});

test('switching to the raider view mid-customise drops the officer widgets', async ({ page }) => {
  await page.goto('login/');
  await page.getByRole('button', { name: 'Sign in as an officer' }).click();
  await page.getByRole('button', { name: 'Customise' }).click();
  await expect(page.getByRole('checkbox', { name: /Raid leader desk/ })).toHaveCount(1);

  await page.getByRole('button', { name: 'Switch to raider view' }).click();
  await expect(page.getByRole('region', { name: 'Customise your home' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Customise' }).click();
  await expect(page.getByRole('checkbox', { name: /Raid leader desk/ })).toHaveCount(0);
  await page.getByRole('region', { name: 'Customise your home' }).getByRole('button', { name: 'Save' }).click();
  await expect(page.locator('[data-widget="officer_desk"]')).toHaveCount(0);
});
