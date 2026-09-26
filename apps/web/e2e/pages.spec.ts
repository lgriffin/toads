import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { ROUTES } from './routes';

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
  await expect(guild.getByRole('link')).toHaveText(['Story', 'Recruit', 'Highlights']);
  const members = page.getByRole('navigation', { name: 'Members' });
  await expect(members.getByRole('link')).toHaveText(['Hub', 'Raids & Logs', 'Bank', 'Me', 'Officers']);
  await members.getByRole('link', { name: 'Hub' }).click();
  await expect(page).toHaveURL(/\/toads\/hub\/$/);
  await expect(members.getByRole('link', { name: 'Hub' })).toHaveAttribute('aria-current', 'page');
});

test('the story page links to recruit and opens Discord safely', async ({ page }) => {
  await page.goto('');
  const discord = page.getByRole('link', { name: 'Join our Discord' });
  await expect(discord).toHaveAttribute('rel', 'noopener noreferrer');
  await page.getByRole('link', { name: 'Apply to raid with us' }).click();
  await expect(page).toHaveURL(/\/toads\/recruit\/$/);
  await expect(page.getByRole('heading', { name: 'How the interview room works' })).toBeVisible();
});
