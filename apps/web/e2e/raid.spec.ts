import { expect, test } from '@playwright/test';
import { signIn } from './auth';

test('a raider sees their own raid night and no officer desk', async ({ page }) => {
  await signIn(page, 'member');
  await page.goto('raid/');
  await expect(page.getByRole('heading', { level: 1, name: 'Wednesday raid' })).toBeVisible();
  await expect(page.getByText('Coming soon', { exact: true })).toBeVisible();
  await expect(page.getByRole('group', { name: 'Raid night' })).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Running Wednesday' })).toHaveCount(0);
});

test('a raid night officer gets the officer desk with the team\'s absences', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('raid/');
  const desk = page.getByRole('region', { name: 'Running Wednesday' });
  await expect(desk).toBeVisible();
  await expect(desk.getByRole('region', { name: 'Wednesday absences' }).getByText('Lilypadd')).toBeVisible();
});

test('a super admin switches between the raid nights', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('raid/');
  const nights = page.getByRole('group', { name: 'Raid night' });
  await expect(nights.getByRole('button', { name: 'Wednesday' })).toHaveAttribute('aria-pressed', 'true');
  await nights.getByRole('button', { name: 'Sunday' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Sunday raid' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Running Sunday' }).getByText('Bogwort')).toBeVisible();
});

test('a raider reports a raid night they will miss and cancels it', async ({ page }) => {
  await signIn(page, 'member');
  await page.goto('calendar/');
  await page.getByLabel('Note for the officers').fill('Dentist');
  const first = page.getByRole('button', { name: /Wednesday raid\. Report an absence$/ }).last();
  await first.click();
  await page.getByRole('button', { name: 'Report absence' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'officers can see you will miss that night' })).toBeVisible();
  const mine = page.getByRole('region', { name: 'Your upcoming absences' });
  await expect(mine.getByText('Dentist')).toBeVisible();
  await mine.getByRole('listitem').filter({ hasText: 'Dentist' }).getByRole('button', { name: /^Cancel/ }).click();
  await expect(mine.getByText('Dentist')).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Team absences' })).toHaveCount(0);
});
