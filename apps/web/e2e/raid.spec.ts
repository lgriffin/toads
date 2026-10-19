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

test('a raid night officer gets the officer desk with the team\'s absences', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('raid/');
  const desk = page.getByRole('region', { name: 'Running Wednesday' });
  await expect(desk).toBeVisible();
  await expect(desk.getByRole('region', { name: 'Wednesday absences' }).getByText('Lilypadd')).toBeVisible();
});

test('a super admin switches between the raid nights', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('raid/');
  const nights = page.getByRole('group', { name: 'Raid night' });
  await expect(nights.getByRole('button', { name: 'Wednesday' })).toHaveAttribute('aria-pressed', 'true');
  await nights.getByRole('button', { name: 'Sunday' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Sunday raid' })).toBeVisible();
  await expect(
    page.getByRole('region', { name: 'Running Sunday' }).getByRole('region', { name: 'Sunday absences' }).getByText('Bogwort')
  ).toBeVisible();
});

test('a raider reports a raid night they will miss and cancels it', async ({ page }) => {
  await signIn(page, 'member');
  await page.goto('calendar/');
  await page.getByLabel('Note for the officers').fill('Dentist');
  const first = page.getByRole('button', { name: /Wednesday raid\. Report an absence$/ }).last();
  await first.click();
  await page.getByRole('button', { name: 'Report absence' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'officers can see you will miss that night' })).toBeVisible();
  const mine = page.getByRole('region', { name: 'Your upcoming absences' });
  await expect(mine.getByText('Dentist')).toBeVisible();
  await mine.getByRole('listitem').filter({ hasText: 'Dentist' }).getByRole('button', { name: /^Cancel/ }).click();
  await expect(mine.getByText('Dentist')).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Team absences' })).toHaveCount(0);
});

test('a raid night officer adds a task to the board and moves it along', async ({ page }) => {
  await signIn(page, 'officer');
  await page.goto('raid/');
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
  await page.goto('raid/');
  await page.getByRole('group', { name: 'Raid night' }).getByRole('button', { name: 'Sunday' }).click();
  const board = page.getByRole('region', { name: 'Officers’ board' });
  await expect(board.getByText('Find a fourth healer for Sunday', { exact: true })).toBeVisible();
  await expect(board.getByText('Restock flasks in the guild bank', { exact: true })).toHaveCount(0);
});

test('a raider sees no officers’ board', async ({ page }) => {
  await signIn(page, 'member');
  await page.goto('raid/');
  await expect(page.getByRole('heading', { level: 1, name: 'Wednesday raid' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Officers’ board' })).toHaveCount(0);
});
