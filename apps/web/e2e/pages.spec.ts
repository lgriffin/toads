import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { ROUTES } from './routes';
import { signIn } from './auth';

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
}

test('the nav splits public and member pages', async ({ page }) => {
  await page.goto('');
  const guild = page.getByRole('navigation', { name: 'Guild' });
  await expect(guild.getByRole('link')).toHaveText(['Home', 'How we raid', 'Story', 'Recruit']);
  const members = page.getByRole('navigation', { name: 'Members' });
  await expect(members.getByRole('link')).toHaveText(['Hub', 'Raids & Logs', 'Highlights', 'Bank', 'Me', 'Officers']);
  await members.getByRole('link', { name: 'Hub' }).click();
  await expect(page).toHaveURL(/\/toads\/hub\/$/);
  await expect(members.getByRole('link', { name: 'Hub' })).toHaveAttribute('aria-current', 'page');
});

test('the landing page says who we are and what we stand for', async ({ page }) => {
  await page.goto('');
  await expect(page.getByRole('heading', { name: 'Toads', level: 1 })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Who we are' })).toBeVisible();
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
  await expect(page.getByRole('heading', { name: 'How the interview room works' })).toBeVisible();
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
  await expect(widgets.first()).toHaveAttribute('data-widget', 'next_raid');
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
  await expect(widgets.first()).toHaveAttribute('data-widget', 'next_raid');
});

test('the hub draws the analyzer widgets from their shared payloads', async ({ page }) => {
  await page.goto('hub/');
  const damage = page.getByRole('region', { name: 'Top damage' });
  await expect(damage.getByRole('columnheader', { name: 'Damage' })).toBeVisible();
  await expect(damage.getByRole('row')).toHaveCount(6);
  const recent = page.getByRole('region', { name: 'Recent raids' });
  await recent.getByRole('link').first().click();
  await expect(page).toHaveURL(/\/toads\/raids\/[a-z]+-\d{4}\/$/);
});

test('raid leaders see the roster\'s badges and members their own', async ({ page }) => {
  await page.goto('hub/');
  const roster = page.getByRole('region', { name: 'Toads badges' });
  await expect(roster.getByText('Hopscotch', { exact: true })).toBeVisible();
  await expect(roster.getByRole('img', { name: /^Loyal Toad, Legendary: 104 raids/ }).first()).toBeVisible();
  await page.goto('me/');
  const mine = page.getByRole('region', { name: 'Your badges' });
  await expect(mine.getByText(/^Hopscotch: \d+ of 11 earned/)).toBeVisible();
  await expect(mine.getByRole('img', { name: /^Flask Bearer, Legendary: 101 raids/ })).toBeVisible();
  await expect(mine.getByRole('img', { name: /^Drummer, not earned yet/ })).toBeVisible();
});

test('a member places the flasks widget and sees who came prepared', async ({ page }) => {
  await page.goto('hub/');
  await page.getByRole('button', { name: 'Customise' }).click();
  await page.getByRole('checkbox', { name: /Flasks and elixirs/ }).check();
  await page.getByRole('region', { name: 'Customise your home' }).getByRole('button', { name: 'Save' }).click();
  const flasks = page.getByRole('region', { name: 'Flasks and elixirs' });
  await expect(flasks).toContainText('6 of 7 prepared');
  await expect(flasks.getByRole('row', { name: /Croakwell/ })).toContainText('None');
  await expect(flasks.getByRole('row', { name: /Hopscotch/ })).toContainText('Flask of Relentless Assault');
});
