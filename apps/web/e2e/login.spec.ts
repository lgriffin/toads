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
  await expect(members.getByRole('link')).toHaveText(['Hub', 'Raid', 'Calendar', 'Logs', 'Highlights', 'Bank', 'Me']);
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
  await expect(page.getByRole('link', { name: 'Officer', exact: true })).toBeVisible();
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

test('a visitor sees how a raid night works without anyone being named', async ({ page }) => {
  await page.goto('');
  const model = page.getByRole('region', { name: 'How a Toads raid night works' });
  await expect(model.getByRole('link')).toHaveText([
    'Prep',
    'Flasks and consumes',
    'Speed',
    'Measured against ourselves',
    'Read how we raid in full'
  ]);
  await expect(page.getByRole('region', { name: 'The guild right now' }).getByText('BT in 1:48:32')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'A raid week in the pond' })).toHaveCount(0);
  // Guild totals only: the sample sheets' low-consumables names and the preview visitor stay behind the login.
  for (const name of ['Croakley', 'Lilypadma', 'Hopscotch']) await expect(page.getByText(name)).toHaveCount(0);

  await model.getByRole('link', { name: 'Flasks and consumes' }).click();
  await expect(page).toHaveURL(/\/toads\/how-we-raid\/#flasks$/);
  const flasks = page.getByRole('article', { name: 'Flasks and elixirs' });
  await expect(flasks.getByText('Buff consumable uptime on bosses, last four raids')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'How we raid', level: 1 })).toBeVisible();
  await expect(page.getByRole('article', { name: 'Loot Council' }).getByText(/thatsmybis\.com/)).toBeVisible();
  await expect(page.getByRole('article', { name: 'Badges' })).toHaveCount(0);
  await expect(page.getByText('We are aiming for two 40-man raiding teams', { exact: false })).toBeVisible();
});

test('a signed-out applicant is asked to sign in with Discord and keeps their answers', async ({ page }) => {
  await page.goto('recruit/');
  await page.getByLabel('Character name').fill('Lilypad');
  await page.getByLabel('Class', { exact: true }).selectOption('Mage');
  await expect(page.getByRole('group', { name: 'Primary role' }).getByLabel('Ranged')).toBeChecked();
  await page.getByRole('group', { name: 'Raid night' }).getByLabel('Wednesday').check();
  await page.getByLabel('Why Toads?').fill('Friends raid here.');
  // The step's own sign-in link keeps the answers too, not only the send button.
  await page.getByRole('link', { name: 'Sign in with Discord', exact: true }).click();
  await expect(page).toHaveURL(/\/login\/$/);
  await page.goto('recruit/');
  await expect(page.getByLabel('Character name')).toHaveValue('Lilypad');
  await page.getByRole('button', { name: 'Sign in with Discord to apply' }).click();
  await expect(page).toHaveURL(/\/login\/$/);
  await page.goto('recruit/');
  await expect(page.getByLabel('Character name')).toHaveValue('Lilypad');
  await expect(page.getByLabel('Why Toads?')).toHaveValue('Friends raid here.');
  await expect(page.getByRole('group', { name: 'Raid night' }).getByLabel('Wednesday')).toBeChecked();
});
