/**
 * The launch hold: until the hub opens with the World of Warcraft: Forever launch, a raider who signs in sees one
 * coming-soon page, and an officer sees the member tabs but each one says what it will hold at launch. A super admin
 * sees exactly what an officer sees, plus the Admin console. It only decides what the web app renders; every route
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

// The pages being built on real data (the hub, the logs from historic TBC raids, the bank) and the officers' console
// open for officers now, so they follow the work as it lands; Highlights and Me keep the Forever notice.
const OPEN_TO_OFFICERS = ['/hub', '/raids', '/bank', '/officers'];

/** What a member page shows this tier while the hold is on. Public pages and visitors are never held here. */
export function launchHold(path: string, tier: Tier, hold = LAUNCH_HOLD): Hold {
  if (!hold || tier === 'visitor' || !isMemberPath(path)) return 'open';
  // A super admin is an officer with the Admin console on top, so they see the officers' pages.
  if (tier === 'officer' || tier === 'admin') return under(path, OPEN_TO_OFFICERS) ? 'open' : 'forever-notice';
  return 'coming-soon';
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
  /**
   * The Me tab shows the officer's own toads instead, as the open /me page does: in the heading and as a "Your toads"
   * row, in place of the greeting and the standing toad, so the page wears each toad once.
   */
  ownToads?: boolean;
  /** Badges to show off under the list, as files under static/logos/ without `.svg`. */
  showcase?: readonly { toad: string; label: string }[];
}

/** The held tabs Leigh asked to preview in full. Only what the hub is being built to do; no dates beyond launch. */
export const TAB_PREVIEW: Record<string, TabPreview> = {
  '/highlights': {
    intent:
      'A place for the fun side of raid night: the clips, the screenshots and the moments the guild still talks about, shared straight from Discord.',
    toad: 'milestones/raider-of-the-month-badge',
    sections: [
      {
        title: 'Coming to highlights',
        items: [
          'Raid clips from YouTube, Twitch and Streamable, playing right on the page.',
          'Screenshots from the Discord screenshots channel, collected after each raid.',
          'Wipes, first kills and silly moments, posted from Discord and approved by an officer before they show.',
          'Member spotlights, only ever with that member’s consent.'
        ]
      }
    ]
  },
  '/me': {
    intent:
      'Your own page: how you are doing against the median for your role, week on week, so you can improve against yourself rather than chase parses.',
    ownToads: true,
    showcase: [
      { toad: 'badges/always-flasked-badge', label: 'Always Flasked' },
      { toad: 'milestones/raids-50-badge', label: '50 Raids' },
      { toad: 'badges/attuned-badge', label: 'Attuned' },
      { toad: 'badges/illidan-down-badge', label: 'Illidan Down' },
      { toad: 'badges/generous-badge', label: 'Generous' }
    ],
    sections: [
      {
        title: 'Coming to your page',
        items: [
          'Your numbers from every logged raid, against the role median.',
          'Your Toads badges, and how close you are to the next tier.',
          'Claim your characters, alts included, as soon as raids start, so every log you appear in counts towards you.',
          'Your bank receipts: everything the bank has handed you, and when.'
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
