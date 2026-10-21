import { expect, test } from '@playwright/test';
import { signIn } from './auth';

// The preview's bank is the real bank page answered from sample data in the browser (src/lib/preview/bank-fake.ts).

test('a raider requests an item, then cancels it', async ({ page }) => {
  await signIn(page, 'member');
  await page.goto('bank/');
  await expect(page.getByRole('heading', { name: 'Guild bank', level: 1 })).toBeVisible();
  await page.getByRole('figure', { name: 'Gail keeps the counter' }).getByRole('link', { name: 'Fill in a slip' }).click();
  await expect(page).toHaveURL(/#req-item$/);
  await expect(page.getByRole('region', { name: 'Banks' }).getByRole('cell', { name: 'Wednesday bank' })).toBeVisible();
  await expect(page.getByText('Officer reserve')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: /who else runs the bank/ })).toHaveCount(0);

  await page.getByRole('button', { name: 'Request Super Mana Potion' }).click();
  await page.getByLabel('Quantity').fill('5');
  await page.getByLabel('For character').fill('Hopscotch');
  await page.getByRole('button', { name: 'Request', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Request for 5 × Super Mana Potion: reserved.' })).toBeVisible();

  const mine = page.getByRole('region', { name: 'My requests' });
  await mine.getByRole('button', { name: 'Cancel request for Super Mana Potion' }).click();
  await expect(mine.getByRole('row', { name: /5 × Super Mana Potion/ })).toContainText('Cancelled');
});

test('a token the super admin mints gives the raider bank upkeep', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('bank/');
  const admin = page.getByRole('region', { name: /Super admins: who else runs the bank/ });
  await expect(admin.getByRole('note')).toContainText('Break-glass admin');
  await expect(admin.getByRole('cell', { name: 'Croakley (1002)' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Bank upkeep: requests and imports' })).toBeVisible();
  await expect(page.getByRole('cell', { name: 'Officer reserve' })).toBeVisible();

  await page.getByLabel('Note (who it is for)').fill('Demo friend');
  await page.getByRole('button', { name: 'Mint token' }).click();
  const token = (await admin.locator('.token code').textContent())?.trim() ?? '';
  expect(token).toMatch(/^demo-/);

  await page.getByRole('button', { name: 'Switch to raider view' }).click();
  await expect(page.getByRole('heading', { name: 'Bank upkeep: requests and imports' })).toHaveCount(0);
  await page.getByLabel('Token', { exact: true }).fill(token);
  await page.getByRole('button', { name: 'Redeem' }).click();
  await expect(page.getByText(/Token redeemed\. You may now import bank snapshots on every bank/)).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Import a bank export' })).toBeVisible();
});

test('an officer approves and delivers a request, then a new capture accounts for it', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('bank/');
  const row = page.getByRole('row', { name: /10 × Super Mana Potion/ });
  await row.getByRole('button', { name: 'Approve Super Mana Potion for Croakley' }).click();
  await expect(row).toContainText('Approved');

  const stock = page.getByRole('region', { name: 'Inventory' }).getByRole('row', { name: /Super Mana Potion/ });
  await expect(stock.getByRole('cell')).toHaveText(['60', '0', '0', '10', '50', /Request/]);
  await row.getByRole('button', { name: 'Record delivery of Super Mana Potion' }).click();
  await expect(stock.getByRole('cell')).toHaveText(['60', '10', '0', '0', '50', /Request/]);

  await page.getByLabel('Export parts').fill('TOADSBANK/1 demo export');
  await page.getByRole('button', { name: 'Add parts' }).click();
  await page.getByRole('button', { name: 'Accept snapshot' }).click();
  await expect(page.getByText(/Snapshot accepted\. Tabs updated: 1, 2, 3\./)).toBeVisible();
  await expect(stock.getByRole('cell')).toHaveText(['50', '0', '0', '0', '50', /Request/]);
});

// The hub's own request desk (docs/bank-desk.md), answered from src/lib/preview/bank-desk-fake.ts.
test('an officer answers a /bankrequest with a message and opens the member’s history', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('bank/');
  const desk = page.getByRole('region', { name: 'Bank requests' });
  await desk.getByRole('button', { name: /^Answer Ribbit’s request for Drums of Battle/ }).click();
  await desk.getByLabel('Message to Ribbit (optional)').fill('Grab them from Gail after the raid');
  await desk.getByRole('button', { name: 'Approve', exact: true }).click();
  await expect(desk.getByRole('status')).toContainText('Approved Ribbit’s Drums of Battle x2. The Toad Bot will DM them.');

  await desk.getByRole('button', { name: /Every request/ }).click();
  const answered = desk.getByRole('row', { name: /Drums of Battle/ });
  await expect(answered).toContainText('Approved');
  await expect(answered).toContainText('Grab them from Gail after the raid');

  await answered.getByRole('button', { name: /^Ribbit/ }).click();
  await expect(desk.getByRole('heading', { name: 'Ribbit’s requests' })).toBeVisible();
});

test('a raider sees only their own bank requests and can ask', async ({ page }) => {
  await signIn(page, 'member');
  await page.goto('bank/');
  const desk = page.getByRole('region', { name: 'Bank requests' });
  await expect(desk.getByRole('button', { name: /Answer/ })).toHaveCount(0);
  await expect(desk.getByText('We are short this week')).toBeVisible();
  await desk.getByLabel('Item').fill('Primal Fire');
  await desk.getByLabel('How many').fill('3');
  await desk.getByRole('button', { name: 'Ask the bank' }).click();
  await expect(desk.getByText('Asked for Primal Fire x3.')).toBeVisible();
});
