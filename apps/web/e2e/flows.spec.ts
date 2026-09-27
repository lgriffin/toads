import { expect, test } from '@playwright/test';

test('the recruit form shows field errors, then success', async ({ page }) => {
  await page.goto('recruit/');
  await page.getByLabel('Character name').fill('Frog1');
  await page.getByLabel('Warcraft Logs link').fill('javascript:alert(1)');
  await page.getByRole('button', { name: 'Send application' }).click();

  const alert = page.getByRole('alert');
  await expect(alert).toBeVisible();
  await expect(alert).toBeFocused();
  await expect(page.locator('#characterName-error')).toContainText('2 to 12 letters');
  await expect(page.locator('#className-error')).toBeVisible();
  await expect(page.locator('#spec-error')).toBeVisible();
  await expect(page.locator('#role-error')).toBeVisible();
  await expect(page.locator('#logsUrl-error')).toBeVisible();
  await expect(page.getByLabel('Character name')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.locator('body')).not.toContainText('Application sent');

  await page.getByLabel('Character name').fill('Pondsküm');
  await page.getByLabel('Class').selectOption('Paladin');
  await page.getByLabel('Spec').selectOption('Holy');
  await expect(page.getByLabel('Role')).toHaveValue('Healer');
  await page.getByLabel('Sunday').check();
  await page.getByLabel(/Raiding experience/).fill('Healed Kara and Gruul.\nKeen to push SSC.');
  await page.getByLabel('Warcraft Logs link').fill('https://classic.warcraftlogs.com/character/eu/spineshatter/pondskum');
  await page.getByRole('button', { name: 'Send application' }).click();

  const done = page.getByRole('status').filter({ hasText: 'Application sent' });
  await expect(done).toBeVisible();
  await expect(done).toContainText('private interview room will open');
  await expect(done).toContainText('Pondsküm');
});

test('an officer moves an application from applied to interviewing', async ({ page }) => {
  await page.goto('officers/');
  const card = page.getByTestId('application-app-1');
  await expect(card.getByText('Applied', { exact: true })).toBeVisible();
  await expect(card.getByText('Interview room open')).toHaveCount(0);

  await card.getByRole('button', { name: /^Open interview room/ }).click();

  await expect(card.getByText('Interviewing', { exact: true })).toBeVisible();
  await expect(card.getByText('Interview room open')).toBeVisible();
  await expect(card).toContainText('#interview-mireborn');
  await expect(card.getByRole('button', { name: /^Offer trial raid/ })).toBeVisible();
  await expect(card.getByRole('button', { name: /^Open interview room/ })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: /^Applied/ })).toHaveCount(0);
});

test('granting spotlight consent on the hub lets officers publish it', async ({ page }) => {
  await page.goto('hub/');
  await expect(page.getByRole('heading', { name: 'Spotlight about you' })).toBeVisible();
  await page.getByRole('button', { name: 'Grant' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Officers can now publish' })).toBeVisible();

  await page.getByRole('link', { name: /Spotlights awaiting consent/ }).click();
  await expect(page).toHaveURL(/\/officers\/#spotlights$/);
  await expect(page.locator('#spotlights').getByText('Consent granted')).toHaveCount(2);
  await page.locator('#spotlights').getByRole('button', { name: 'Publish' }).click();
  await expect(page.locator('#spotlights').getByRole('status')).toContainText('Published the spotlight on Hopscotch');
});

test('curating a Discord post publishes it to the hub feed', async ({ page }) => {
  await page.goto('officers/');
  const queue = page.locator('#curation');
  await expect(queue.getByText('Edited since review')).toBeVisible();
  await queue.getByRole('article').filter({ hasText: 'Lurker spout tip' }).getByRole('button', { name: 'Publish to guild' }).click();
  await expect(queue.getByRole('status')).toContainText('Published “Lurker spout tip”');
  await page.getByRole('navigation', { name: 'Members' }).getByRole('link', { name: 'Hub' }).click();
  await expect(page.locator('article').filter({ hasText: 'Lurker spout tip' })).toContainText('from Discord');
});
