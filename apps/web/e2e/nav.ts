import type { Page } from '@playwright/test';

// The top bar's menus (src/routes/+layout.svelte): Hub, Officers and the account menu each open a panel of links.

export async function openHubMenu(page: Page) {
  await page.getByRole('navigation', { name: 'Main' }).getByRole('button', { name: 'Hub' }).click();
  return page.locator('#menu-hub');
}

export async function openOfficersMenu(page: Page) {
  await page.getByRole('navigation', { name: 'Main' }).getByRole('button', { name: 'Officers' }).click();
  return page.locator('#menu-officers');
}

export async function openAccountMenu(page: Page) {
  await page.getByRole('banner').getByRole('button', { name: /^Account/ }).click();
  return page.locator('#menu-account');
}
