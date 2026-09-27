import { expect, test } from '@playwright/test';
import { CLIP_HOSTS } from './routes';

for (const route of ['story/', 'highlights/', 'hub/', 'officers/']) {
  test(`/${route} makes no clip provider request until a clip is played`, async ({ page }) => {
    const hits: string[] = [];
    page.on('request', (req) => {
      if (CLIP_HOSTS.test(new URL(req.url()).hostname)) hits.push(req.url());
    });
    // Never touch the real providers from the test run; answer any embed request locally.
    await page.route(
      (url) => CLIP_HOSTS.test(url.hostname),
      (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>clip</title>' })
    );

    await page.goto(route);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('iframe')).toHaveCount(0);
    expect(hits).toEqual([]);

    const play = page.getByRole('button', { name: /^Play / }).first();
    await play.click();
    const frame = page.locator('iframe').first();
    await expect(frame).toHaveAttribute('sandbox', 'allow-scripts allow-same-origin allow-presentation');
    await expect(frame).toHaveAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    await expect(frame).toHaveAttribute('title', /.+/);
    expect(await frame.getAttribute('src')).toMatch(
      /^https:\/\/(www\.youtube-nocookie\.com\/embed\/|clips\.twitch\.tv\/embed\?|streamable\.com\/e\/)/
    );
    await expect.poll(() => hits.length).toBeGreaterThan(0);
  });
}
