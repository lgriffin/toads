/**
 * The launch hold: until the hub opens with the World of Warcraft: Forever launch, a raider who signs in sees one
 * coming-soon page, and an officer sees the real member pages as they are built, except the bank, which says what it
 * will hold at launch. A super admin sees exactly what an officer sees, plus the Admin console. It only decides what the web app renders; every route
 * still checks its own permission. Lift it by setting LAUNCH_HOLD to false.
 */
import type { Tier } from './access';
import { MEMBER_EXTRA, MEMBER_NAV, type NavItem } from './nav';

/** The real site holds; the static preview keeps the full sample-data demo unless built with LAUNCH_HOLD=1. */
export const LAUNCH_HOLD: boolean = __LAUNCH_HOLD__;

export const FOREVER_LAUNCH = { date: '2026-11-04', label: '4 November 2026' } as const;

export type Hold = 'open' | 'coming-soon' | 'forever-notice';

// The admin console is super admins' only and never held; it keeps its own refusal for everyone else.
const MEMBER = [...MEMBER_NAV.filter((i) => !i.adminOnly).map((i) => i.href), ...MEMBER_EXTRA];

/** True for the held member pages (the Members nav except Admin, and the welcome checklist); `path` is relative to the base path. */
export function isMemberPath(path: string): boolean {
  return under(path, MEMBER);
}

function under(path: string, prefixes: readonly string[]): boolean {
  const p = path.length > 1 && path.endsWith('/') ? path.slice(0, -1) : path || '/';
  return prefixes.some((prefix) => p === prefix || p.startsWith(`${prefix}/`));
}

// Officers and super admins use the real pages as they are built; only the bank, which has no data yet, keeps its
// Forever preview.
const HELD_FOR_OFFICERS = ['/bank'];

// Open to raiders during the hold too: the Raid page is itself a coming-soon page for each raid night, and Me is where
// raiders tell their officers which nights they will miss, which matters before launch too. Me alone, not its claim and
// settings pages; while the hold is on it shows a raider only their absences (`absencesOnly`). The first sign-in setup
// is open too: officers want every member's main, specs and alts before launch (docs/setup.md).
const OPEN_TO_MEMBERS = ['/raid'];
const OPEN_TO_MEMBERS_EXACT = ['/me', '/setup'];

function exactly(path: string, paths: readonly string[]): boolean {
  const p = path.length > 1 && path.endsWith('/') ? path.slice(0, -1) : path || '/';
  return paths.includes(p);
}

/** True while the hold keeps a raider's Me page to their absences: the rest of it is the Logs analysis, held. */
export function absencesOnly(tier: Tier, hold = LAUNCH_HOLD): boolean {
  return hold && tier === 'raider';
}

/** What a member page shows this tier while the hold is on. Public pages and visitors are never held here. */
export function launchHold(path: string, tier: Tier, hold = LAUNCH_HOLD): Hold {
  if (!hold || tier === 'visitor' || !isMemberPath(path)) return 'open';
  // A super admin is an officer with the Admin console on top, so they see the officers' pages.
  if (tier === 'officer' || tier === 'admin') return under(path, HELD_FOR_OFFICERS) ? 'forever-notice' : 'open';
  return under(path, OPEN_TO_MEMBERS) || exactly(path, OPEN_TO_MEMBERS_EXACT) ? 'open' : 'coming-soon';
}

/** A raider's Members nav during the hold: the hub link, which opens the coming-soon page, then the open pages. */
export function heldNav(nav: NavItem[], tier: Tier, hold = LAUNCH_HOLD): NavItem[] {
  const open = [...OPEN_TO_MEMBERS, ...OPEN_TO_MEMBERS_EXACT];
  return hold && tier === 'raider' ? nav.filter((i) => i.href === '/hub' || open.includes(i.href)) : nav;
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
  '/raid': 'Each raid night’s home: your role, sign-ups and prep, with an officer desk for the night’s officers.',
  '/logs': 'Every logged raid with guild totals, role medians and reference comparisons.',
  '/highlights': 'Raid night photos with a photo of the week, members’ live streams, and clips.',
  '/bank': 'Bank requests, imports and each raid night’s stock.',
  '/me': 'Each member’s own numbers, badges, character claims and the raid nights they will miss.',
  '/officers': 'Character claims, applications, the badge roster, log syncs and each team’s absences.',
  '/welcome': 'The first sign-in checklist for new members.'
};

export interface PreviewSection {
  title: string;
  items: readonly string[];
}

/** A held tab's fuller preview: why it exists and what is coming to it, for the officers' Forever launch notice. */
export interface TabPreview {
  intent: string;
  sections: readonly PreviewSection[];
  /** A toad under static/logos/, without `.svg`, standing beside the intent. */
  toad?: string;
  /** The bank tab also shows a mockup of the bank at work. */
  mockup?: 'bank';
}

/** The held tab's full preview. Only what the hub is being built to do; no dates beyond launch. */
export const TAB_PREVIEW: Record<string, TabPreview> = {
  '/bank': {
    intent:
      'The bank exists to get raiders what they need for raid night, fairly and on the record: flasks, potions and mats go where the raid needs them, and anyone can see who got what and when.',
    toad: 'ranks/banker-badge',
    mockup: 'bank',
    sections: [
      {
        title: 'For every member',
        items: [
          'See what the bank holds, kept up to date from the bank characters by the Toads bank addon.',
          'Ask for what you need from the site or straight from Discord with /bank request.',
          'Follow your request from asked to handed over, and keep a receipt of everything you have received.'
        ]
      },
      {
        title: 'For bankers, and visible to officers',
        items: [
          'One queue of requests from Discord and the site, oldest first, with each raider’s attendance beside it.',
          'Mark a request handed over in game and it lands in the ledger with the banker’s name and the time.',
          'Low-stock warnings before raid night, so the guild can farm or buy ahead of the pull.',
          'A fairness view: what each raider has received against the raids they attended, so nobody is quietly favoured or forgotten.'
        ]
      }
    ]
  }
};

/** The tab a member path belongs to, for the notice's heading and purpose. */
export function tabOf(path: string): NavItem | undefined {
  const p = path.length > 1 && path.endsWith('/') ? path.slice(0, -1) : path || '/';
  const under = (href: string) => p === href || p.startsWith(`${href}/`);
  const tab = MEMBER_NAV.find((i) => under(i.href));
  if (tab) return tab;
  return under('/welcome') ? { href: '/welcome', label: 'Welcome' } : undefined;
}
