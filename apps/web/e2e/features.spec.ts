import { expect, test, type Page } from '@playwright/test';
import { signIn } from './auth';

// Hub features lists what each tier can do in the three apps; columns above the viewer's tier show dimmed and say who
// holds them. Super admins see it as officers do, and the page never mentions them.
const step = (page: Page, app: string, tier: string) =>
  page.getByRole('region', { name: app }).locator(`[data-tier="${tier}"]`);

test('a visitor finds Hub features in the public nav, with only the public column open', async ({ page }) => {
  await page.goto('');
  await page.getByRole('navigation').getByRole('link', { name: 'Hub features' }).first().click();
  await expect(page).toHaveURL(/\/toads\/features\/$/);
  await expect(page.getByRole('heading', { name: 'Hub features', level: 1 })).toBeVisible();
  await expect(page.getByText('You are not signed in.')).toBeVisible();
  for (const app of ['Raid analyzer', 'Guild bank', 'Discord and Drive']) {
    await expect(step(page, app, 'visitor')).not.toHaveClass(/locked/);
    await expect(step(page, app, 'raider')).toHaveClass(/locked/);
    await expect(step(page, app, 'admin')).toHaveCount(0);
  }
  await expect(step(page, 'Guild bank', 'raider')).toContainText('Log in with Discord to unlock');
  await expect(page.locator('#main').getByText(/super admin/i)).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'How to get more' })).toHaveCount(0);
});

test('the old toolkit address lands on Hub features', async ({ page }) => {
  await page.goto('toolkit/');
  await expect(page).toHaveURL(/\/toads\/features\/$/);
});

test('a raider has the raider column and sees what officers hold', async ({ page }) => {
  await signIn(page, 'member');
  await page.goto('');
  await page.getByRole('link', { name: 'Raider', exact: true }).click();
  await expect(page).toHaveURL(/\/toads\/features\/$/);
  await expect(step(page, 'Raid analyzer', 'raider')).not.toHaveClass(/locked/);
  await expect(step(page, 'Raid analyzer', 'raider')).toHaveClass(/here/);
  await expect(step(page, 'Raid analyzer', 'officer')).toContainText('For the officers of each raid night');
  await expect(step(page, 'Discord and Drive', 'raider')).toContainText('Your role for the night from the officers’ Drive sheet');
});

test('an officer unlocks every column', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('features/');
  await expect(step(page, 'Discord and Drive', 'officer')).toContainText('Write the strategy and role sheets in Google Drive');
  await expect(page.locator('.step.locked')).toHaveCount(0);
});

test('a super admin sees the officer view, and only they see grants in the bank', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('features/');
  await expect(page.locator('.step.locked')).toHaveCount(0);
  await expect(step(page, 'Guild bank', 'officer')).toHaveClass(/here/);
  await expect(page.locator('#main').getByText(/super admin/i)).toHaveCount(0);
  // signIn re-applies the view on every load, so move on by link after switching.
  await page.getByRole('button', { name: 'Switch to officer view' }).click();
  await page.getByRole('navigation', { name: 'Members' }).getByRole('link', { name: 'Bank' }).click();
  await expect(page.getByRole('heading', { name: 'Bank upkeep: requests and imports' })).toBeVisible();
  await expect(page.getByRole('region', { name: /Super admins: who else runs the bank/ })).toHaveCount(0);
});
