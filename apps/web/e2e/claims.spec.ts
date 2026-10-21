import { expect, test } from '@playwright/test';
import { signIn } from './auth';

test('a night\'s officer approves and rejects their own night\'s claims only', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('officers/claims/');
  const wed = page.getByRole('region', { name: 'Wednesday claims' });
  await expect(wed.getByText('Toadstool', { exact: true })).toBeVisible();
  await expect(wed.getByText('also on Sunday')).toBeVisible();
  await expect(page.getByText('Pondweed', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Members on no raid night' })).toHaveCount(0);

  await wed.getByRole('button', { name: 'Approve Puddles’s claim on Toadstool' }).click();
  await expect(wed.getByRole('status')).toHaveText('Toadstool is now Puddles’s.');
  await wed.getByRole('button', { name: 'Reject Lily’s claim on Lilypadd' }).click();
  await wed.getByLabel('Why? Lily reads this on Me').fill('That is someone else’s alt');
  await wed.getByRole('button', { name: 'Reject claim' }).click();
  await expect(wed.getByText('No claims are waiting.')).toBeVisible();
});

test('a super admin sees every night\'s claims and members on no night', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('officers/claims/');
  for (const name of ['Wednesday claims', 'Thursday claims', 'Sunday claims', 'Members on no raid night']) {
    await expect(page.getByRole('region', { name })).toBeVisible();
  }
  await expect(page.getByRole('region', { name: 'Members on no raid night' }).getByText('Marshmallow', { exact: true })).toBeVisible();
});

test('a night\'s officer section holds its claims', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('officers/nights/thu/');
  await expect(page.getByRole('region', { name: 'Character claims' }).getByText('Bramblewick', { exact: true })).toBeVisible();
});
