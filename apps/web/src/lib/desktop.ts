/**
 * What the desktop app (apps/desktop, docs/desktop.md) reads from the live site, served at /desktop.json: the lists
 * the top bar is drawn from and whether the launch hold is on. The app also bundles this module, and uses the bundled
 * copy only until the site answers, so a site deploy (a new page in a menu, the launch hold lifted) reaches the app
 * at once, without a new release. Bump DESKTOP_CONTRACT when a field changes meaning; the app ignores a contract it
 * does not know and keeps its bundled menus.
 */
import { LAUNCH_HOLD } from './launch';
import { NAV, type NavItem, type NavLists } from './nav';

export const DESKTOP_CONTRACT = 1;

export const DESKTOP_PATH = '/desktop.json';

export interface DesktopSite {
  contract: number;
  launch_hold: boolean;
  nav: NavLists;
}

/** The site's answer at /desktop.json. */
export function desktopSite(hold: boolean = LAUNCH_HOLD, nav: NavLists = NAV): DesktopSite {
  return { contract: DESKTOP_CONTRACT, launch_hold: hold, nav };
}

// A hub path: one leading slash and plain path characters, so a link can never name another site ("//host").
const PATH = /^\/(?!\/)[A-Za-z0-9\-_/]*$/;
const LISTS: readonly (keyof NavLists)[] = ['publicNav', 'memberNav', 'hubMenu', 'officerMenu', 'accountMenu'];

function item(raw: unknown): NavItem | null {
  if (!raw || typeof raw !== 'object') return null;
  const i = raw as Record<string, unknown>;
  if (typeof i.href !== 'string' || !PATH.test(i.href) || typeof i.label !== 'string' || !i.label.trim()) return null;
  return {
    href: i.href,
    label: i.label,
    ...(i.officerOnly === true ? { officerOnly: true } : {}),
    ...(i.adminOnly === true ? { adminOnly: true } : {}),
    ...(typeof i.hint === 'string' ? { hint: i.hint } : {})
  };
}

/** The site's answer, or null for anything that is not one this app understands (an older or newer contract, an error page). */
export function parseDesktopSite(body: unknown): DesktopSite | null {
  if (!body || typeof body !== 'object') return null;
  const b = body as Record<string, unknown>;
  if (b.contract !== DESKTOP_CONTRACT || typeof b.launch_hold !== 'boolean') return null;
  const nav = b.nav as Record<string, unknown> | undefined;
  if (!nav || typeof nav !== 'object') return null;
  const lists: Partial<Record<keyof NavLists, NavItem[]>> = {};
  for (const key of LISTS) {
    const raw = nav[key];
    if (!Array.isArray(raw)) return null;
    const items = raw.map(item);
    if (items.some((i) => i === null)) return null;
    lists[key] = items as NavItem[];
  }
  return { contract: DESKTOP_CONTRACT, launch_hold: b.launch_hold, nav: lists as NavLists };
}
