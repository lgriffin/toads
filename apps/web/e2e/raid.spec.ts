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

test('a raid night officer goes from the officer desk to their night\'s own section', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('raid/');
  const desk = page.getByRole('region', { name: 'Running Wednesday' });
  await desk.getByRole('link', { name: 'Open Wednesday’s officer section' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Wednesday officers' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Wednesday absences' }).getByText('Lilypadd')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Wednesday interview panel' })).toBeVisible();
});

test('a night\'s officer sees tonight first and pins and unpins a Drive link', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('officers/nights/wed/');
  const tonight = page.getByRole('region', { name: /^Next Wednesday/ });
  await expect(tonight.getByRole('group', { name: 'Who is away' }).getByText('Lilypadd')).toBeVisible();
  const links = tonight.getByRole('group', { name: 'Strategy and roles' });
  await expect(links.getByRole('link', { name: 'Kael’thas strategy' })).toHaveAttribute('target', '_blank');
  await links.getByLabel('Name').fill('Vashj roles');
  await links.getByLabel('Link').fill('http://example.com/roles');
  await links.getByRole('button', { name: 'Pin link' }).click();
  await expect(links.getByRole('status')).toContainText('https');
  await links.getByLabel('Link').fill('https://docs.google.com/spreadsheets/d/vashj');
  await links.getByRole('button', { name: 'Pin link' }).click();
  await expect(links.getByRole('link', { name: 'Vashj roles' })).toBeVisible();
  await links.getByRole('button', { name: 'Unpin Vashj roles' }).click();
  await expect(links.getByRole('link', { name: 'Vashj roles' })).toHaveCount(0);
  await expect(links.getByRole('status')).toHaveText('Unpinned “Vashj roles”.');
});

test('a night\'s officers see only their own night\'s section', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('officers/');
  const nights = page.getByRole('region', { name: 'Your raid night' });
  await expect(nights.getByRole('link')).toHaveText(['Wednesday officers']);
  await page.goto('officers/nights/sun/');
  await expect(page.getByText('another raid night\'s officer section')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Officers’ board' })).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Sunday absences' })).toHaveCount(0);
});

test('a super admin sees every night\'s section', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('officers/');
  const nights = page.getByRole('region', { name: 'Your raid nights' });
  await expect(nights.getByRole('link')).toHaveText(['Wednesday officers', 'Thursday officers', 'Sunday officers']);
  await nights.getByRole('link', { name: 'Thursday officers' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Thursday officers' })).toBeVisible();
  await page.getByRole('link', { name: 'Build Thursday\'s comp' }).click();
  await expect(page.getByLabel('Raid night')).toHaveValue('thu');
});

test('moving between night sections shows each night\'s own interview panel', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('officers/nights/wed/');
  await expect(page.getByRole('region', { name: 'Wednesday interview panel' })).toBeVisible();
  await page.goto('officers/nights/sun/');
  await expect(page.getByRole('region', { name: 'Sunday interview panel' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Wednesday interview panel' })).toHaveCount(0);
});

test('a super admin switches between the raid nights', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('raid/');
  const nights = page.getByRole('group', { name: 'Raid night' });
  await expect(nights.getByRole('button', { name: 'Wednesday' })).toHaveAttribute('aria-pressed', 'true');
  await nights.getByRole('button', { name: 'Sunday' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Sunday raid' })).toBeVisible();
  await page.getByRole('region', { name: 'Running Sunday' }).getByRole('link', { name: 'Open Sunday’s officer section' }).click();
  await expect(page.getByRole('region', { name: 'Sunday absences' }).getByText('Bogwort')).toBeVisible();
});

test('a raider adds a raid night they will miss on Me, changes it and deletes it', async ({ page }) => {
  await signIn(page, 'member');
  await page.goto('me/');
  const absences = page.getByRole('region', { name: 'Your absences' });
  const first = absences.getByRole('button', { name: /Wednesday raid\. Report an absence$/ }).last();
  await first.click();
  // Every absence carries a note for the officers.
  await expect(absences.getByRole('button', { name: 'Report absence' })).toBeDisabled();
  await absences.getByLabel('Note for the officers').fill('Dentist');
  await absences.getByRole('button', { name: 'Report absence' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'officers can see you will miss that night' })).toBeVisible();
  const mine = page.getByRole('region', { name: 'Your upcoming absences' });
  const row = mine.getByRole('listitem').filter({ hasText: 'Dentist' });
  await row.getByRole('button', { name: /^Change/ }).click();
  await absences.getByLabel('Note for the officers').fill('Dentist, moved to the evening');
  await absences.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.getByRole('status').filter({ hasText: /^Changed\./ })).toBeVisible();
  const changed = mine.getByRole('listitem').filter({ hasText: 'Dentist, moved to the evening' });
  // Delete asks once more, and Keep it backs out.
  await changed.getByRole('button', { name: /^Delete/ }).click();
  await expect(changed.getByRole('button', { name: 'Keep it' })).toBeFocused();
  await changed.getByRole('button', { name: 'Keep it' }).click();
  await expect(changed.getByRole('button', { name: /^Delete/ })).toBeFocused();
  await changed.getByRole('button', { name: /^Delete/ }).click();
  await changed.getByRole('button', { name: 'Delete absence' }).click();
  await expect(mine.getByText('Dentist')).toHaveCount(0);
});

test('officers read their team\'s absences under Officers, and old Calendar links land on Me', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('officers/');
  await page.getByRole('link', { name: 'Open the Calendar' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Calendar' })).toBeVisible();
  const team = page.getByRole('region', { name: 'Team absences' });
  await expect(team.getByText('Half-term holiday.').first()).toBeVisible();
  await page.goto('calendar/');
  await expect(page).toHaveURL(/\/me\/(#absences)?$/);
});

test('a raid night officer adds a task to the board and moves it along', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('officers/nights/wed/');
  const board = page.getByRole('region', { name: 'Officers’ board' });
  await expect(board.getByRole('region', { name: /^To do/ }).getByText('Restock flasks in the guild bank', { exact: true })).toBeVisible();
  await expect(board.getByText('Overdue')).toBeVisible();
  await board.getByLabel('New task').fill('Post the Karazhan groups');
  await board.getByLabel('Assign to').selectOption({ label: 'Ribbit' });
  await board.getByRole('button', { name: 'Add card' }).click();
  const todo = board.getByRole('region', { name: /^To do/ });
  await expect(todo.getByRole('listitem').filter({ hasText: 'Post the Karazhan groups' })).toContainText('Ribbit');
  await board.getByRole('button', { name: /^Start it\W+Post the Karazhan groups$/ }).click();
  await expect(board.getByRole('region', { name: /^In progress/ }).getByText('Post the Karazhan groups', { exact: true })).toBeVisible();
  await board.getByRole('button', { name: 'Edit Post the Karazhan groups' }).click();
  await board.getByRole('button', { name: 'Remove' }).click();
  await board.getByRole('button', { name: 'Remove for good' }).click();
  await expect(board.getByText('Post the Karazhan groups', { exact: true })).toHaveCount(0);
});

test('each raid night has its own board, and raiders see none', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('officers/nights/sun/');
  const board = page.getByRole('region', { name: 'Officers’ board' });
  await expect(board.getByText('Find a fourth healer for Sunday', { exact: true })).toBeVisible();
  await expect(board.getByText('Restock flasks in the guild bank', { exact: true })).toHaveCount(0);
});

test('a raider sees no officers’ board', async ({ page }) => {
  await signIn(page, 'member');
  await page.goto('raid/');
  await expect(page.getByRole('heading', { level: 1, name: 'Wednesday raid' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Officers’ board' })).toHaveCount(0);
  await page.goto('officers/nights/wed/');
  await expect(page.getByRole('region', { name: 'Officers’ board' })).toHaveCount(0);
});
