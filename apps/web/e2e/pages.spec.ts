import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { ROUTES } from './routes';
import { signIn } from './auth';
import { openAccountMenu, openHubMenu, openOfficersMenu } from './nav';

// Member pages open after the preview's pretend sign-in; most tests explore as an officer.
test.beforeEach(({ page }) => signIn(page, 'officer'));

for (const route of ROUTES) {
  const name = `/${route}`;

  test(`${name} loads without console errors`, async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    page.on('pageerror', (err) => errors.push(err.message));
    const res = await page.goto(route);
    expect(res?.status()).toBe(200);
    await expect(page.locator('h1')).toBeVisible();
    await page.waitForLoadState('networkidle');
    expect(errors).toEqual([]);
  });

  test(`${name} has no horizontal scroll at 390px`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(route);
    await page.waitForLoadState('networkidle');
    const width = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(width).toBeLessThanOrEqual(390);
  });

  test(`${name} has no serious or critical axe violations`, async ({ page }) => {
    await page.goto(route);
    await page.waitForLoadState('networkidle');
    const results = await new AxeBuilder({ page }).analyze();
    const bad = results.violations
      .filter((v) => v.impact === 'serious' || v.impact === 'critical')
      .map((v) => `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(' ')).join(', ')})`);
    expect(bad).toEqual([]);
  });

  test(`${name} has no serious or critical axe violations in the light theme with easier reading`, async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('toads-theme', 'light');
      localStorage.setItem('toads-reading', 'easy');
    });
    await page.goto(route);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
    const results = await new AxeBuilder({ page }).analyze();
    const bad = results.violations
      .filter((v) => v.impact === 'serious' || v.impact === 'critical')
      .map((v) => `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(' ')).join(', ')})`);
    expect(bad).toEqual([]);
  });
}

for (const theme of ['dark', 'light']) {
  test(`the open top bar menus have no serious or critical axe violations (${theme})`, async ({ page }) => {
    await page.addInitScript((t) => localStorage.setItem('toads-theme', t), theme);
    await signIn(page, 'admin');
    await page.goto('hub/');
    for (const open of [openHubMenu, openOfficersMenu, openAccountMenu]) {
      await open(page);
      const results = await new AxeBuilder({ page }).include('header').analyze();
      const bad = results.violations
        .filter((v) => v.impact === 'serious' || v.impact === 'critical')
        .map((v) => `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(' ')).join(', ')})`);
      expect(bad).toEqual([]);
      await page.keyboard.press('Escape');
    }
  });
}

test('a signed-in officer has Hub, Me and one Officers menu in the top bar', async ({ page }) => {
  await page.goto('');
  await expect(page.getByRole('navigation', { name: 'Guild' })).toHaveCount(0);
  const main = page.getByRole('navigation', { name: 'Main' });
  await expect(main.getByRole('button')).toHaveText(['Hub', 'Officers']);
  await expect(main.getByRole('link')).toHaveText(['Me']);

  const hub = await openHubMenu(page);
  await expect(main.getByRole('button', { name: 'Hub' })).toHaveAttribute('aria-expanded', 'true');
  await expect(hub.getByRole('link')).toHaveText([
    /^Hub home/, /^Raid/, /^Logs/, /^Highlights/, /^Bank/, 'Home', 'How we raid', 'Hub features', 'Story', 'Recruit'
  ]);
  await page.keyboard.press('Escape');
  await expect(hub).toBeHidden();
  await expect(main.getByRole('button', { name: 'Hub' })).toBeFocused();

  await (await openHubMenu(page)).getByRole('link', { name: /^Logs/ }).click();
  await expect(page).toHaveURL(/\/toads\/logs\/$/);
  await expect(page.locator('#menu-hub')).toBeHidden();
  await expect((await openHubMenu(page)).getByRole('link', { name: /^Logs/ })).toHaveAttribute('aria-current', 'page');

  // The Wednesday raid leader sees the officer tools and Wednesday's section, never another night's or the Admin console.
  const officers = await openOfficersMenu(page);
  await expect(officers.getByRole('link', { name: /^Wednesday officers/ })).toBeVisible();
  await expect(officers.getByRole('link', { name: /^Sunday officers/ })).toHaveCount(0);
  await expect(officers.getByRole('link', { name: /^Admin console/ })).toHaveCount(0);
});

const signOut = (page: Page) => page.addInitScript(() => localStorage.removeItem('toads-preview-role'));

test('a visitor keeps the public nav', async ({ page }) => {
  await signOut(page);
  await page.goto('');
  const guild = page.getByRole('navigation', { name: 'Guild' });
  await expect(guild.getByRole('link')).toHaveText(['Home', 'How we raid', 'Hub features', 'Story', 'Recruit']);
  await expect(page.getByRole('navigation', { name: 'Main' })).toHaveCount(0);
});

test('the display settings switch to the light theme and easier reading, and remember them', async ({ page }) => {
  await page.goto('hub/');
  const root = page.locator('html');
  await expect(root).toHaveAttribute('data-theme', 'dark');
  const account = await openAccountMenu(page);
  await account.getByRole('radio', { name: 'Light' }).check();
  await expect(root).toHaveAttribute('data-theme', 'light');
  await account.getByRole('checkbox', { name: /Easier reading/ }).check();
  await expect(root).toHaveAttribute('data-reading', 'easy');
  await page.reload();
  await expect(root).toHaveAttribute('data-theme', 'light');
  await expect(root).toHaveAttribute('data-reading', 'easy');
});

test('a visitor picks a theme from the Display menu', async ({ page }) => {
  await signOut(page);
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto('');
  await page.getByRole('banner').getByRole('button', { name: 'Display' }).click();
  await page.getByRole('radio', { name: 'Match my device' }).check();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
});

test('the landing page says who we are and what we stand for', async ({ page }) => {
  await page.goto('');
  await expect(page.getByRole('heading', { name: 'Toads', level: 1 })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Who we are', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Who we are looking for' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'What we stand for' })).toBeVisible();
  // The preview visitor is signed in, so the call to action is their hub rather than the login.
  await page.getByRole('link', { name: 'Go to your hub' }).click();
  await expect(page).toHaveURL(/\/toads\/hub\/$/);
});

test('the story page links to recruit and opens Discord safely', async ({ page }) => {
  await page.goto('story/');
  const discord = page.getByRole('link', { name: 'Join our Discord' });
  await expect(discord).toHaveAttribute('rel', 'noopener noreferrer');
  await page.getByRole('link', { name: 'Apply to raid with us' }).click();
  await expect(page).toHaveURL(/\/toads\/recruit\/$/);
  await expect(page.getByRole('heading', { name: 'Your application' })).toBeVisible();
});

test('the hub shows the latest raid totals from the sheets', async ({ page }) => {
  await page.goto('hub/');
  const totals = page.getByRole('region', { name: 'Raid totals' });
  await expect(totals).toBeVisible();
  await expect(totals.getByText('1:48:32', { exact: true })).toBeVisible();
  await expect(totals.getByText('40 across 21 players')).toBeVisible();
  const report = totals.getByRole('link', { name: /Warcraft Logs report/ });
  await expect(report).toHaveAttribute('rel', 'noopener noreferrer');
  await expect(report).toHaveAttribute('target', '_blank');
  await expect(report).toHaveAttribute('href', /^https:\/\/classic\.warcraftlogs\.com\/reports\/[A-Za-z0-9]{16}$/);
  const rows = totals.getByRole('table', { name: 'Recent raids' }).locator('tbody tr');
  await expect(rows).toHaveCount(5);
});

test('a member customises their hub home', async ({ page }) => {
  await page.goto('hub/');
  const widgets = page.locator('[data-widget]');
  // The home leads with the member's own last raid against their role's median.
  await expect(widgets.first()).toHaveAttribute('data-widget', 'my_performance');
  await expect(page.getByRole('heading', { level: 2, name: /Hopscotch beat the melee median by 14%/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Recruiting' })).toHaveCount(0);

  await page.getByRole('button', { name: 'Customise' }).click();
  const panel = page.getByRole('region', { name: 'Customise your home' });
  await panel.getByRole('checkbox', { name: /Next raid/ }).uncheck();
  await panel.getByRole('checkbox', { name: /Recruiting/ }).check();
  const up = panel.getByRole('button', { name: 'Move Recruiting up' });
  // Recruiting starts last; move it to the top.
  for (let i = 0; i < 30 && !(await up.isDisabled()); i++) await up.click();
  await expect(up).toBeDisabled();
  await panel.getByRole('button', { name: 'Save' }).click();

  await expect(panel).toHaveCount(0);
  await expect(widgets.first()).toHaveAttribute('data-widget', 'recruiting');
  await expect(page.locator('[data-widget="next_raid"]')).toHaveCount(0);

  await page.getByRole('button', { name: 'Customise' }).click();
  await panel.getByRole('button', { name: 'Reset to default' }).click();
  await expect(widgets.first()).toHaveAttribute('data-widget', 'my_performance');
});

test('Logs draws the analyzer widgets from their shared payloads', async ({ page }) => {
  await page.goto('logs/');
  const damage = page.getByRole('region', { name: 'Top damage' });
  await expect(damage.getByRole('columnheader', { name: 'Damage' })).toBeVisible();
  await expect(damage.getByRole('row')).toHaveCount(6);
  const flasks = page.getByRole('region', { name: 'Flasks and elixirs' });
  await expect(flasks).toContainText('6 of 7 prepared');
  await expect(flasks.getByRole('row', { name: /Hopscotch/ })).toContainText('Flask of Relentless Assault');
  // A raid opens its breakdown on the hub, under the night a Wednesday officer reads in full.
  const recent = page.getByRole('region', { name: 'Recent raids' });
  await recent.getByRole('link').first().click();
  await expect(page).toHaveURL(/\/toads\/logs\/[a-z]+-\d{4}\/\?day=wed$/);
});

test('the hub home leaves the raid widgets to Logs', async ({ page }) => {
  await page.goto('hub/');
  await expect(page.locator('[data-widget="next_raid"]')).toBeVisible();
  for (const name of ['Guild at a glance', 'Top damage', 'Recent raids', 'Toads badges']) {
    await expect(page.getByRole('region', { name, exact: true })).toHaveCount(0);
  }
  await page.getByRole('button', { name: 'Customise' }).click();
  await expect(page.getByRole('checkbox', { name: /Flasks and elixirs/ })).toHaveCount(0);
});

test('raid leaders see the roster\'s badges on Logs and members their own on Me', async ({ page }) => {
  await page.goto('logs/');
  const roster = page.getByRole('region', { name: 'Toads badges' });
  await expect(roster.getByText('Hopscotch', { exact: true })).toBeVisible();
  await expect(roster.getByRole('img', { name: /^Loyal Toad, Legendary: 104 raids/ }).first()).toBeVisible();
  await page.goto('me/');
  const mine = page.getByRole('region', { name: 'Your badges' });
  await expect(mine.getByText(/^Hopscotch: \d+ of 11 earned/)).toBeVisible();
  await expect(mine.getByRole('img', { name: /^Flask Bearer, Legendary: 101 raids/ })).toBeVisible();
  await expect(mine.getByRole('img', { name: /^Drummer, not earned yet/ })).toBeVisible();
});

test('Me shows a member their own raids against the role median, and switches character', async ({ page }) => {
  await page.goto('me/');
  const raids = page.getByRole('region', { name: 'Your raids' });
  await expect(raids.getByText(/^Hopscotch, Rogue: 5 guild raids since \d{4}-/)).toBeVisible();
  await expect(raids.getByRole('img', { name: /^Damage as melee/ })).toBeVisible();
  await expect(raids.getByRole('columnheader', { name: 'Role median' })).toBeVisible();
  const pick = raids.getByLabel('Character');
  await expect(pick.locator('option:checked')).toHaveText('Hopscotch (main)');
  await pick.selectOption('Lilypadd');
  await expect(raids.getByText(/^Building your history/)).toBeVisible();
  await expect(raids.getByRole('img', { name: /^Healing as healer/ })).toHaveCount(0);
  // Each raid opens its page under Logs.
  await raids.getByRole('link', { name: 'Tempest Keep' }).first().click();
  await expect(page).toHaveURL(/\/toads\/logs\/pondThu1015\/$/);
});

test('a member asks an officer to make the alt they are looking at their main', async ({ page }) => {
  await page.goto('me/');
  const raids = page.getByRole('region', { name: 'Your raids' });
  await expect(raids.getByRole('button', { name: /Make .* my main$/ }).first()).toBeVisible();
  await expect(raids.getByRole('button', { name: 'Make Lilypadd my main' })).toHaveCount(0);
  await raids.getByLabel('Character').selectOption('Lilypadd');
  await raids.getByRole('button', { name: 'Make Lilypadd my main' }).click();
  await expect(raids).toContainText('Waiting for an officer to make Lilypadd your main instead of Hopscotch.');
  await raids.getByRole('button', { name: 'Withdraw' }).click();
  await expect(raids.getByRole('status').filter({ hasText: 'Withdrew' })).toHaveText('Withdrew your main swap.');
});

test('the tab shows the toad icon, and every icon file loads under the base path', async ({ page, request }) => {
  await page.goto('./');
  const hrefs = await page.locator('link[rel="icon"], link[rel="apple-touch-icon"]').evaluateAll((links) =>
    links.map((link) => (link as HTMLLinkElement).href)
  );
  expect(hrefs).toHaveLength(3);
  for (const href of hrefs) {
    expect(href).toContain('/toads/');
    expect((await request.get(href)).status()).toBe(200);
  }
});
