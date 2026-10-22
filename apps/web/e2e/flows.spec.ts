import { expect, test } from '@playwright/test';
import { signIn } from './auth';
import { openHubMenu } from './nav';

// Member pages open after the preview's pretend sign-in; most tests explore as an officer.
test.beforeEach(({ page }) => signIn(page, 'officer'));

test('the recruit form shows field errors, then opens the interview room', async ({ page }) => {
  await page.goto('recruit/');
  await expect(page.getByRole('link', { name: /Join the Toads Discord/ }).first()).toHaveAttribute(
    'href',
    'https://discord.gg/toads'
  );
  await page.getByLabel('Character name').fill('Frog1');
  await page.getByRole('button', { name: 'Send application' }).click();

  const alert = page.getByRole('alert');
  await expect(alert).toBeVisible();
  await expect(alert).toBeFocused();
  await expect(page.locator('#characterName-error')).toContainText('2 to 24 letters');
  await expect(page.locator('#className-error')).toBeVisible();
  await expect(page.locator('#primaryRole-error')).toBeVisible();
  await expect(page.locator('#raidDay-error')).toBeVisible();
  await expect(page.locator('#whyToads-error')).toBeVisible();
  await expect(page.getByLabel('Character name')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.locator('body')).not.toContainText('interview room is opening');

  await page.getByLabel('Character name').fill('Pondsküm');
  await page.getByLabel('Class', { exact: true }).selectOption('Paladin');
  const primary = page.getByRole('group', { name: 'Primary role' });
  const secondary = page.getByRole('group', { name: 'Secondary role' });
  await expect(primary.getByLabel('Ranged')).toBeDisabled(); // Paladins have no ranged spec
  await primary.getByLabel('Healer').check();
  await expect(secondary.getByLabel('Healer')).toBeDisabled(); // not the same role twice
  await secondary.getByLabel('Tank').check();
  await page.getByRole('group', { name: 'Raid night' }).getByLabel('Sunday').check();
  await page.getByLabel('Why Toads?').fill('Healed Kara and Gruul.\nA friend says Sundays are the best nights.');
  await page.getByRole('button', { name: 'Send application' }).click();

  const done = page.getByRole('status').filter({ hasText: 'interview room is opening' });
  await expect(done).toBeVisible();
  await expect(done).toContainText('#interview-pondskum');
  await expect(done).toContainText('Pondsküm');
});

test('an officer puts someone from the Discord on their night’s interview panel', async ({ page }) => {
  await page.goto('officers/recruitment/');
  const wed = page.getByRole('region', { name: 'Wednesday interview panel' });
  await expect(wed.getByText('@_gallagher')).toBeVisible();
  await wed.getByLabel('Add someone from the Toads Discord').fill('hop');
  await wed.getByRole('button', { name: 'Find' }).click();
  await wed.getByRole('button', { name: 'Add Hopscotch to the Wednesday panel' }).click();
  await expect(wed.getByRole('status')).toContainText('Hopscotch now interviews Wednesday applicants.');
  await wed.getByRole('button', { name: 'Remove Hopscotch from the Wednesday panel' }).click();
  await expect(wed.getByRole('button', { name: 'Remove Hopscotch from the Wednesday panel' })).toHaveCount(0);
  // A Wednesday officer has no Sunday panel to change.
  await expect(page.getByRole('region', { name: 'Sunday interview panel' })).toHaveCount(0);
});

test('officers note a night’s applicant, then accept them on the Decisions panel', async ({ page }) => {
  await page.goto('officers/recruitment/');
  const wed = page.getByRole('region', { name: 'Wednesday decisions' });
  await expect(wed.getByText('Knows the Vashj fight well.')).toBeVisible();
  await wed.getByLabel('Note on Mossbeard').fill('Happy to take them.');
  await wed.getByRole('button', { name: 'Add note' }).first().click();
  await expect(wed.getByText('Happy to take them.')).toBeVisible();
  await wed.getByRole('button', { name: 'Accept Mossbeard' }).click();
  await expect(wed.getByText(/the Toad Bot gives them the Wednesday raider role/)).toBeVisible();
  await wed.getByRole('button', { name: 'Accept Mossbeard' }).click();
  await expect(wed.getByRole('status')).toContainText('Mossbeard is accepted for Wednesday.');
  await expect(wed.getByRole('heading', { name: 'Mossbeard' })).toHaveCount(0);
  await wed.getByText(/Decided in the last two weeks/).click();
  await expect(wed.getByText('Toad Bot: Gave Mossbeard the Wednesday raider role in Discord.')).toBeVisible();
});

test('granting spotlight consent on the hub tells the member officers can publish it', async ({ page }) => {
  await page.goto('hub/');
  await expect(page.getByRole('heading', { name: 'Spotlight about you' })).toBeVisible();
  await page.getByRole('button', { name: 'Grant' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Officers can now publish' })).toBeVisible();
});

