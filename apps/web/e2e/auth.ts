import type { Page } from '@playwright/test';

/** The preview's pretend sign-in keeps the chosen view here (see src/lib/preview/session.svelte.ts). */
export const ROLE_KEY = 'toads-preview-role';

/** Start every page load in this test signed in with the given view, as if the visitor had used /login. */
export async function signIn(page: Page, role: 'member' | 'officer') {
  await page.addInitScript(([key, value]) => localStorage.setItem(key, value), [ROLE_KEY, role] as const);
}
