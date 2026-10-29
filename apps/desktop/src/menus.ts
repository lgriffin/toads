/**
 * The app's Hub, Me and Officers menus. They are the website's own top bar, worked out the same way +layout.svelte does
 * from the member's /api/session, so an officer sees only the raid nights they run and a raider during the launch hold
 * sees what the site shows them. The rules (apps/web/src/lib/nav.ts, launch.ts, access.ts) are bundled in, not copied;
 * the lists they draw from and the launch hold come from the live site's /desktop.json (apps/web/src/lib/desktop.ts),
 * so a site deploy reaches the menus without a new release. The bundled lists are used only until the site answers.
 * Like the site's, these menus only hide links: every page still checks its own permission.
 */
import { tierOf, type Tier } from '../../web/src/lib/access';
import { dayName, raidDaysOf } from '../../web/src/lib/absences';
import type { Session } from '../../web/src/lib/api';
import { desktopSite, type DesktopSite } from '../../web/src/lib/desktop';
import { accountMenu, heldNav } from '../../web/src/lib/launch';
import { SIGN_IN, SIGN_OUT, hubMenu, memberNav, officerMenu, type NavGroup, type NavItem } from '../../web/src/lib/nav';

/** The site as this build knows it, until the live site's /desktop.json answers. */
export const BUNDLED_SITE: DesktopSite = desktopSite();

export interface Link {
  label: string;
  /** A path on the hub. */
  path: string;
  /** Electron's accelerator syntax, e.g. CmdOrCtrl+1. */
  accelerator?: string;
  /** Log out: the app posts to `path` as the site's account menu does, instead of opening it. */
  signOut?: true;
}

/** One menu: groups of links, drawn with a separator between groups. */
export interface MenuSpec {
  label: string;
  groups: Link[][];
}

export interface Menus {
  tier: Tier;
  /** The Hub, Me and (for officers and super admins) Officers menus, in top bar order. */
  menus: MenuSpec[];
  /** Officers' shortcuts for the tray: the console and their raid nights. Empty for raiders and visitors. */
  officerQuickLinks: Link[];
}

function links(group: NavGroup, accelerator?: (i: number) => string): Link[] {
  return group.items.map((item, i) => ({
    label: item.label,
    path: item.href,
    ...(accelerator && i < 9 ? { accelerator: accelerator(i) } : {})
  }));
}

/** The menus for a member, or a visitor when `session` is null. */
export function menusFor(session: Session | null, site: DesktopSite = BUNDLED_SITE): Menus {
  const { nav, launch_hold: hold } = site;
  const tier = tierOf(session);
  const officer = (session?.officer_days.length ?? 0) > 0;
  const members = session ? heldNav(memberNav(officer, tier === 'admin', nav.memberNav), tier, hold) : [];
  const hub = hubMenu(members, nav.hubMenu, nav.publicNav).filter((g) => g.items.length);
  // CmdOrCtrl+1.. for the member's own hub pages, as the site's Hub menu orders them.
  const hubMenuSpec: MenuSpec = {
    label: 'Hub',
    groups: hub.map((g, i) => links(g, i === 0 ? (n) => `CmdOrCtrl+${n + 1}` : undefined))
  };
  const menus: MenuSpec[] = [hubMenuSpec, { label: 'Me', groups: meGroups(session, tier, members.some((i) => i.href === '/me'), site) }];

  const days = raidDaysOf(session);
  const officerGroups = officerMenu(
    officer,
    tier === 'admin',
    days.officerDays.map((day) => ({ day, name: dayName(day, days.names) })),
    nav.officerMenu
  );
  if (officerGroups.length) {
    // CmdOrCtrl+Shift+1.. for the officer tools, in the site's order.
    menus.push({
      label: 'Officers',
      groups: officerGroups.map((g, i) => links(g, i === 0 ? (n) => `CmdOrCtrl+Shift+${n + 1}` : undefined))
    });
  }
  const quick = officerGroups.filter((g) => g.label !== 'Super admin').flatMap((g) => g.items);
  return {
    tier,
    menus,
    officerQuickLinks: quick
      .filter((i) => i.href === '/officers' || i.href.startsWith('/officers/nights/'))
      .map((i) => ({ label: i.label, path: i.href }))
  };
}

const asLinks = (items: readonly NavItem[]): Link[] => items.map((i) => ({ label: i.label, path: i.href }));

/** The site's account menu: Me, then its account pages for the member's rank; a visitor gets the site's sign-in. */
function meGroups(session: Session | null, tier: Tier, meOpen: boolean, site: DesktopSite): Link[][] {
  const features = site.nav.accountMenu.filter((i) => i.href === '/features');
  if (!session) return [[{ label: SIGN_IN.label, path: SIGN_IN.href }], asLinks(features)].filter((g) => g.length);
  const mine: Link[] = meOpen ? [{ label: 'Me', path: '/me', accelerator: 'CmdOrCtrl+0' }] : [];
  const account = asLinks(accountMenu(tier, site.launch_hold, site.nav.accountMenu));
  const out: Link[] = [{ label: SIGN_OUT.label, path: SIGN_OUT.href, signOut: true }];
  return [mine, account, out].filter((g) => g.length);
}

/** The session as /api/session answers it, or null for anything that is not one (signed out, an error page). */
export function parseSession(body: unknown): Session | null {
  if (!body || typeof body !== 'object') return null;
  const s = body as Partial<Session>;
  if (typeof s.member_id !== 'number' || !Array.isArray(s.officer_days) || !Array.isArray(s.raid_days)) return null;
  return body as Session;
}
