import { expect, test, type Page } from '@playwright/test';
import { signIn } from './auth';

// The toolkit lists what each tier can do in the three apps; rows above the viewer's tier show dimmed and say who
// holds them.
const row = (page: Page, app: string, tier: string) =>
  page.getByRole('region', { name: app }).locator(`[data-tier="${tier}"]`);

test('a visitor sees every app with only the public rows open', async ({ page }) => {
  await page.goto('toolkit/');
  await expect(page.getByRole('heading', { name: 'Your toolkit', level: 1 })).toBeVisible();
  await expect(page.getByText('You are not signed in.')).toBeVisible();
  for (const app of ['Raid analyzer', 'Guild bank', 'Discord and Drive']) {
    await expect(row(page, app, 'visitor')).not.toHaveClass(/locked/);
    await expect(row(page, app, 'raider')).toHaveClass(/locked/);
  }
  await expect(row(page, 'Guild bank', 'raider')).toContainText('Log in with Discord to unlock');
});

test('a raider has the raider rows and sees what officers and super admins hold', async ({ page }) => {
  await signIn(page, 'member');
  await page.goto('');
  await page.getByRole('link', { name: 'Raider', exact: true }).click();
  await expect(page).toHaveURL(/\/toads\/toolkit\/$/);
  await expect(row(page, 'Raid analyzer', 'raider')).not.toHaveClass(/locked/);
  await expect(row(page, 'Raid analyzer', 'officer')).toContainText('For the officers of each raid night');
  await expect(row(page, 'Discord and Drive', 'raider')).toContainText('Your role for the night from the officers’ Drive sheet');
  await expect(row(page, 'Guild bank', 'admin')).toHaveClass(/locked/);
});

test('an officer unlocks the officer rows but not the super admin ones', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('toolkit/');
  await expect(row(page, 'Discord and Drive', 'officer')).toContainText('Write the strategy and role sheets in Google Drive');
  await expect(row(page, 'Discord and Drive', 'officer')).not.toHaveClass(/locked/);
  await expect(row(page, 'Guild bank', 'admin')).toContainText('For super admins only');
});

test('a super admin has everything, and only they see grants in the bank', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('toolkit/');
  await expect(page.locator('.row.locked')).toHaveCount(0);
  // signIn re-applies the view on every load, so move on by link after switching.
  await page.getByRole('button', { name: 'Switch to officer view' }).click();
  await page.getByRole('navigation', { name: 'Members' }).getByRole('link', { name: 'Bank' }).click();
  await expect(page.getByRole('heading', { name: 'Bank upkeep: requests and imports' })).toBeVisible();
  await expect(page.getByRole('region', { name: /Super admins: who else runs the bank/ })).toHaveCount(0);
});
