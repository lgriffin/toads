import { expect, test } from '@playwright/test';
import { signIn } from './auth';

test('a new member finds the welcome checklist from the homepage', async ({ page }) => {
  await signIn(page, 'member');
  await page.goto('');
  await page.getByRole('link', { name: 'Start with the checklist' }).click();
  await expect(page).toHaveURL(/\/toads\/welcome\/$/);
  await expect(page.getByRole('heading', { name: 'Welcome to the pond', level: 1 })).toBeVisible();
  await expect(page.getByRole('listitem')).toHaveCount(6);
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
