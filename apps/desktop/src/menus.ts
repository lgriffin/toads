/**
 * The app's Hub, Me and Officers menus. They are the website's own top bar (apps/web/src/lib/nav.ts, launch.ts and
 * access.ts are bundled in, not copied), worked out the same way +layout.svelte does from the member's /api/session, so
 * an officer sees only the raid nights they run and a raider during the launch hold sees what the site shows them.
 * Like the site's, these menus only hide links: every page still checks its own permission.
 */
import { tierOf, type Tier } from '../../web/src/lib/access';
import { dayName, raidDaysOf } from '../../web/src/lib/absences';
import type { Session } from '../../web/src/lib/api';
import { heldNav, launchHold } from '../../web/src/lib/launch';
import { hubMenu, memberNav, officerMenu, type NavGroup } from '../../web/src/lib/nav';

export interface Link {
  label: string;
  /** A path on the hub. */
  path: string;
  /** Electron's accelerator syntax, e.g. CmdOrCtrl+1. */
  accelerator?: string;
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

const SIGN_IN: Link = { label: 'Sign in with Discord', path: '/auth/login' };

function links(group: NavGroup, accelerator?: (i: number) => string): Link[] {
  return group.items.map((item, i) => ({
    label: item.label,
    path: item.href,
    ...(accelerator && i < 9 ? { accelerator: accelerator(i) } : {})
  }));
}

/** The menus for a member, or a visitor when `session` is null. */
export function menusFor(session: Session | null): Menus {
  const tier = tierOf(session);
  const officer = (session?.officer_days.length ?? 0) > 0;
  const members = session ? heldNav(memberNav(officer, tier === 'admin'), tier) : [];
  const hub = hubMenu(members).filter((g) => g.items.length);
  // CmdOrCtrl+1.. for the member's own hub pages, as the site's Hub menu orders them.
  const hubMenuSpec: MenuSpec = {
    label: 'Hub',
    groups: hub.map((g, i) => links(g, i === 0 ? (n) => `CmdOrCtrl+${n + 1}` : undefined))
  };
  const menus: MenuSpec[] = [hubMenuSpec, { label: 'Me', groups: meGroups(session, tier, members.some((i) => i.href === '/me')) }];

  const days = raidDaysOf(session);
  const officerGroups = officerMenu(
    officer,
    tier === 'admin',
    days.officerDays.map((day) => ({ day, name: dayName(day, days.names) }))
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

/** The site's account menu: Me, then settings, setup and what the member's rank opens; a visitor gets sign-in. */
function meGroups(session: Session | null, tier: Tier, meOpen: boolean): Link[][] {
  if (!session) return [[SIGN_IN], [{ label: 'What you can do', path: '/features' }]];
  const mine: Link[] = meOpen ? [{ label: 'Me', path: '/me', accelerator: 'CmdOrCtrl+0' }] : [];
  const account: Link[] = [
    ...(launchHold('/me/settings', tier) === 'open' ? [{ label: 'Account settings', path: '/me/settings' }] : []),
    { label: 'Your setup', path: '/setup' },
    { label: 'What you can do', path: '/features' }
  ];
  return [mine, account].filter((g) => g.length);
}

/** The session as /api/session answers it, or null for anything that is not one (signed out, an error page). */
export function parseSession(body: unknown): Session | null {
  if (!body || typeof body !== 'object') return null;
  const s = body as Partial<Session>;
  if (typeof s.member_id !== 'number' || !Array.isArray(s.officer_days) || !Array.isArray(s.raid_days)) return null;
  return body as Session;
}
