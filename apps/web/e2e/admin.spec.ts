import { expect, test } from '@playwright/test';
import { signIn } from './auth';

test('a new member finds the welcome checklist from the homepage', async ({ page }) => {
  await signIn(page, 'member');
  await page.goto('');
  await page.getByRole('link', { name: 'Start with the checklist' }).click();
  await expect(page).toHaveURL(/\/toads\/welcome\/$/);
  await expect(page.getByRole('heading', { name: 'Welcome to the pond', level: 1 })).toBeVisible();
  await expect(page.getByRole('main').getByRole('listitem')).toHaveCount(6);
  const download = page.getByRole('link', { name: 'Download the analyzer' });
  await expect(download).toHaveAttribute('rel', 'noopener noreferrer');
  await page.getByRole('link', { name: 'Claim a character' }).click();
  await expect(page).toHaveURL(/\/toads\/me\/claim\/$/);
});

test('only the super admin view opens the admin console', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('admin/');
  await expect(page.getByRole('heading', { name: 'Super admins only' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Members' }).getByRole('link', { name: 'Admin' })).toHaveCount(0);
});

test('a super admin sees integrations, jobs and grants on the admin console', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('hub/');
  await page.getByRole('navigation', { name: 'Members' }).getByRole('link', { name: 'Admin' }).click();
  await expect(page.getByRole('heading', { name: 'Admin console', level: 1 })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Integrations' }).getByRole('heading', { name: 'Google Drive' })).toBeVisible();
  await expect(page.getByRole('cell', { name: 'import-sheets' })).toBeVisible();
  const grants = page.getByRole('region', { name: /Super admins: who else runs the bank/ });
  await expect(grants.getByRole('cell', { name: 'Croakley (1002)' })).toBeVisible();
});

test('a super admin posts for either raid night', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('officers/');
  await page.getByLabel('Audience').selectOption('raid_day');
  await expect(page.getByLabel('Raid day').getByRole('option')).toHaveText(['Wednesday', 'Thursday', 'Sunday']);
  await page.getByLabel('Raid day').selectOption('Sunday');
  await page.getByLabel('Title').fill('Sunday kara');
  await page.getByLabel('Body').fill('Bring fire resistance gear for the opera.');
  await page.getByRole('button', { name: 'Publish post' }).click();
  await expect(page.getByText('Posted “Sunday kara”')).toBeVisible();
});

test('an officer adds reference reports from the officer console', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('officers/');
  await page.getByRole('region', { name: 'Reference reports' }).getByRole('link', { name: 'Add reference reports' }).click();
  await expect(page).toHaveURL(/\/toads\/officers\/reference\/$/);
  await expect(page.getByRole('heading', { name: 'Reference comparison', level: 1 })).toBeVisible();
});

test('a Wednesday officer posts for Wednesday only', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('officers/');
  await page.getByLabel('Audience').selectOption('raid_day');
  await expect(page.getByLabel('Raid day').getByRole('option')).toHaveText(['Wednesday']);
});

test('a super admin gives a badge to a Discord role and takes it off again', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('admin/');
  const desk = page.getByRole('region', { name: 'Badges from Discord roles' });
  await desk.getByLabel('Discord role').selectOption({ label: 'Tank' });
  await desk.getByRole('radio', { name: 'Tank' }).check({ force: true });
  await desk.getByRole('button', { name: 'Give the badge to this role' }).click();
  await expect(desk.getByText('Everyone with the Tank role now wears the Tank badge.')).toBeVisible();
  await desk.getByRole('button', { name: 'Remove Tank from Tank' }).click();
  await expect(desk.getByText('The Tank role no longer earns the Tank badge.')).toBeVisible();
});

test('a super admin wears the super admin and member toads', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('hub/');
  const header = page.getByRole('banner');
  await expect(header.getByRole('img', { name: 'Super admin', exact: true })).toBeVisible();
  await expect(header.getByRole('img', { name: 'Member', exact: true })).toBeVisible();
  await expect(header.getByRole('img', { name: 'Wednesday Toad' })).toBeVisible();
});

test('a super admin sees the same toads on their own page as beside their name', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('me/');
  const heading = page.getByRole('heading', { name: /Your performance/, level: 1 });
  for (const name of ['Super admin', 'Member', 'Wednesday Toad', 'Healer']) {
    await expect(heading.getByRole('img', { name, exact: true })).toBeVisible();
  }
  const card = page.getByRole('region', { name: 'Your toads' });
  for (const name of ['Super admin', 'Member', 'Wednesday Toad', 'Healer']) {
    await expect(card.getByText(name, { exact: true })).toBeVisible();
  }
});
