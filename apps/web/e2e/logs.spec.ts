import { expect, test } from '@playwright/test';
import { signIn } from './auth';

test('the day chips cut the raid list to the picked weekdays', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('logs/');
  const raids = page.getByRole('region', { name: 'Raids', exact: true });
  await expect(raids.getByText('6 of 6 raids, every day.')).toBeVisible();
  const days = page.getByRole('group', { name: 'Raid days' });
  await days.getByRole('button', { name: /^Wed/ }).click();
  await days.getByRole('button', { name: /^Thu/ }).click();
  await expect(raids.getByText('4 of 6 raids, Wednesday, Thursday.')).toBeVisible();
  await expect(raids.getByRole('cell', { name: 'Sunday' })).toHaveCount(0);
  await days.getByRole('button', { name: 'Every day' }).click();
  await expect(raids.getByText('6 of 6 raids, every day.')).toBeVisible();
});

test('a super admin opens a raid and moves through the analysis tabs', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('logs/pondThu1015/');
  await expect(page.getByRole('heading', { level: 1, name: 'Tempest with the toads' })).toBeVisible();
  const tabs = page.getByRole('group', { name: 'Analysis' });
  await tabs.getByRole('button', { name: 'Healers' }).click();
  await expect(page.getByRole('heading', { level: 2, name: 'Healers' })).toBeVisible();
  await expect(page.getByRole('rowheader', { name: /Lilypadd/ })).toBeVisible();
  await tabs.getByRole('button', { name: 'Boss vs trash' }).click();
  await expect(page.getByRole('columnheader', { name: 'On trash' })).toBeVisible();
});

test('Logs opens on the raid night of the Toad badge, with every raid a tab away', async ({ page }) => {
  await signIn(page, 'member');
  await page.goto('logs/');
  const nights = page.getByRole('group', { name: 'Raid night' });
  await expect(nights.getByRole('button', { name: 'Wednesday' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('heading', { level: 2, name: 'Wednesday at a glance' })).toBeVisible();
  await expect(page.getByRole('heading', { level: 2, name: 'Last raid' })).toBeVisible();
  // Members never get the roster's badges.
  await expect(page.getByRole('heading', { level: 2, name: 'Toads badges' })).toHaveCount(0);
  const raids = page.getByRole('region', { name: 'Raids', exact: true });
  await expect(raids.getByText(/ of 6 raids, Wednesday\.$/)).toBeVisible();
  await expect(raids.getByRole('cell', { name: 'Thursday' })).toHaveCount(0);
  await nights.getByRole('button', { name: 'Every raid' }).click();
  await expect(page.getByRole('heading', { level: 2, name: 'Every raid at a glance' })).toBeVisible();
  await expect(raids.getByText('6 of 6 raids, every day.')).toBeVisible();
});

test('a super admin opens Logs on every raid', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('logs/');
  const nights = page.getByRole('group', { name: 'Raid night' });
  await expect(nights.getByRole('button', { name: 'Every raid' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('heading', { level: 2, name: 'Toads badges' })).toBeVisible();
});

test('a Wednesday officer sees Wednesday raids in full and other nights as an overview', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('logs/');
  await page.getByRole('group', { name: 'Raid night' }).getByRole('button', { name: 'Thursday' }).click();
  const raids = page.getByRole('region', { name: 'Raids', exact: true });
  await raids.getByRole('link').first().click();
  await expect(page.getByText("Each raider's numbers are for this night's officers.")).toBeVisible();
  await expect(page.getByRole('group', { name: 'Analysis' })).toHaveCount(0);
  await page.goto('logs/');
  await expect(raids.getByText(/ of 6 raids, Wednesday\.$/)).toBeVisible();
  const wednesday = raids.getByRole('row').filter({ hasText: 'Wednesday' }).first();
  await expect(wednesday.getByText('Full')).toBeVisible();
  await wednesday.getByRole('link').click();
  await expect(page).toHaveURL(/\?day=wed$/);
  await expect(page.getByRole('group', { name: 'Analysis' })).toBeVisible();
});
