/**
 * The launch hold: until the hub opens with the World of Warcraft: Forever launch, a raider who signs in sees one
 * coming-soon page, an officer sees the member tabs but each one says what it will hold at launch, and super admins
 * see everything. It only decides what the web app renders; every route still checks its own permission. Lift it by
 * setting LAUNCH_HOLD to false.
 */
import type { Tier } from './access';
import { MEMBER_EXTRA, MEMBER_NAV, type NavItem } from './nav';

/** The real site holds; the static preview keeps the full sample-data demo unless built with LAUNCH_HOLD=1. */
export const LAUNCH_HOLD: boolean = __LAUNCH_HOLD__;

export const FOREVER_LAUNCH = { date: '2026-11-04', label: '4 November 2026' } as const;

export type Hold = 'open' | 'coming-soon' | 'forever-notice';

// The admin console is super admins' only, and they are never held; it keeps its own refusal for everyone else.
const MEMBER = [...MEMBER_NAV.filter((i) => !i.adminOnly).map((i) => i.href), ...MEMBER_EXTRA];

/** True for the held member pages (the Members nav except Admin, and the welcome checklist); `path` is relative to the base path. */
export function isMemberPath(path: string): boolean {
  const p = path.length > 1 && path.endsWith('/') ? path.slice(0, -1) : path || '/';
  return MEMBER.some((prefix) => p === prefix || p.startsWith(`${prefix}/`));
}

/** What a member page shows this tier while the hold is on. Public pages and visitors are never held here. */
export function launchHold(path: string, tier: Tier, hold = LAUNCH_HOLD): Hold {
  if (!hold || tier === 'visitor' || tier === 'admin' || !isMemberPath(path)) return 'open';
  return tier === 'officer' ? 'forever-notice' : 'coming-soon';
}

/** A raider's Members nav during the hold: the hub link alone, which opens the coming-soon page. */
export function heldNav(nav: NavItem[], tier: Tier, hold = LAUNCH_HOLD): NavItem[] {
  return hold && tier === 'raider' ? nav.filter((i) => i.href === '/hub') : nav;
}

export interface Upcoming {
  id: 'bank' | 'logs' | 'raid';
  title: string;
  body: string;
  /** A toad under static/logos/, without `.svg`. */
  toad: string;
}

/** The three things the coming-soon page promises. Only what the hub is being built to do; no dates beyond launch. */
export const UPCOMING: readonly Upcoming[] = [
  {
    id: 'bank',
    title: 'Guild bank management',
    body: 'See what the bank holds and request flasks, potions and mats for raid night. Bankers fill requests from the same list, so nothing gets lost in a Discord thread.',
    toad: 'ranks/banker-badge'
  },
  {
    id: 'logs',
    title: 'Logs analysis',
    body: 'Every raid broken down from Warcraft Logs: guild totals week on week, your own number against the median for your role, and the badges you have earned.',
    toad: 'milestones/raids-50-badge'
  },
  {
    id: 'raid',
    title: 'Raid assistance',
    body: 'Your role for the night, the raid leader’s posts and the prep we ask for, in one place before the pull timer starts.',
    toad: 'ranks/officer-badge'
  }
];

/** What each member tab will hold, for the officers' Forever launch notice. Keyed by the nav href. */
export const TAB_PURPOSE: Record<string, string> = {
  '/hub': 'The raid leader desk, the officers’ posts and each member’s hub home.',
  '/raids': 'Every logged raid with guild totals, role medians and reference comparisons.',
  '/highlights': 'Highlight reels and consent-gated spotlights from raid night.',
  '/bank': 'Bank requests, imports and each raid night’s stock.',
  '/me': 'Each member’s own numbers, badges and character claims.',
  '/officers': 'Character claims, applications, the badge roster and log syncs.',
  '/welcome': 'The first sign-in checklist for new members.'
};

/** The tab a member path belongs to, for the notice's heading and purpose. */
export function tabOf(path: string): NavItem | undefined {
  const p = path.length > 1 && path.endsWith('/') ? path.slice(0, -1) : path || '/';
  const under = (href: string) => p === href || p.startsWith(`${href}/`);
  const tab = MEMBER_NAV.find((i) => under(i.href));
  if (tab) return tab;
  return under('/welcome') ? { href: '/welcome', label: 'Welcome' } : undefined;
}
