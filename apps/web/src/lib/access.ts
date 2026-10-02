/**
 * The toolkit: what each tier can do in the three apps a Toads member gets (the raid analyzer, the guild bank and
 * Discord with the officers' Google Drive). It mirrors the hub's RBAC table (services/api/src/toads_api/rbac/
 * permissions.py), and access.test.ts fails if a permission named here is missing there or sits in another tier. The
 * page only explains; every route still checks its own permission.
 */
import type { Session } from './api';

export type Tier = 'visitor' | 'raider' | 'officer' | 'admin';

export const TIERS: readonly Tier[] = ['visitor', 'raider', 'officer', 'admin'];

export const TIER_LABEL: Record<Tier, string> = {
  visitor: 'Visitor',
  raider: 'Raider',
  officer: 'Officer',
  admin: 'Super admin'
};

/** Shown on a row the viewer has not unlocked: who holds it, or how to get it. */
export const LOCKED: Record<Tier, string> = {
  visitor: 'Open to everyone',
  raider: 'Log in with Discord to unlock',
  officer: 'For the officers of each raid night',
  admin: 'For super admins only'
};

export interface Capability {
  text: string;
  /** The hub permission behind it (its value in permissions.py); none for public pages or things outside the hub. */
  permission?: string;
}

export interface Row {
  tier: Tier;
  can: Capability[];
}

export interface App {
  id: 'analyzer' | 'bank' | 'discord';
  title: string;
  where: string;
  rows: Row[];
}

export const APPS: readonly App[] = [
  {
    id: 'analyzer',
    title: 'Raid analyzer',
    where: 'The hub’s raid pages, the Windows app and the command line',
    rows: [
      {
        tier: 'visitor',
        can: [{ text: 'Progression and clear times' }, { text: 'How we raid, with guild totals' }]
      },
      {
        tier: 'raider',
        can: [
          { text: 'Every guild raid log, broken down', permission: 'view_guild_raids' },
          { text: 'Your role number against the guild median', permission: 'view_own_performance' },
          { text: 'Your badges and the next tier', permission: 'view_own_performance' },
          { text: 'Claim your characters', permission: 'claim_character' },
          { text: 'Use your own Warcraft Logs key' },
          { text: 'Install the Windows app' }
        ]
      },
      {
        tier: 'officer',
        can: [
          { text: 'Anyone’s numbers and the roster’s badges', permission: 'view_others' },
          { text: 'Reference raid comparisons', permission: 'view_insights' },
          { text: 'Sync logs and set roles', permission: 'sync_logs' },
          { text: 'Approve character claims', permission: 'approve_claims' }
        ]
      },
      {
        tier: 'admin',
        can: [{ text: 'Connect the guild’s Warcraft Logs login' }, { text: 'Refresh schedule and job health' }]
      }
    ]
  },
  {
    id: 'bank',
    title: 'Guild bank',
    where: 'The Bank page, the ToadsBank addon and the bank bot',
    rows: [
      { tier: 'visitor', can: [{ text: 'Raid stock of flasks and potions for members' }] },
      {
        tier: 'raider',
        can: [
          { text: 'Browse what every bank holds', permission: 'view_bank' },
          { text: 'Request items on the site or with /bank request', permission: 'request_bank_items' },
          { text: 'Your receipts on Me' },
          { text: 'Redeem an officer’s token to help run the bank' }
        ]
      },
      {
        tier: 'officer',
        can: [
          { text: 'Run your night’s request queue', permission: 'manage_bank' },
          { text: 'Import bank snapshots from the addon', permission: 'import_bank_snapshot' }
        ]
      },
      {
        tier: 'admin',
        can: [
          { text: 'Give bank grants and single-use officer tokens', permission: 'manage_grants' },
          { text: 'Every bank, with break-glass changes audited' }
        ]
      }
    ]
  },
  {
    id: 'discord',
    title: 'Discord and Drive',
    where: 'The Toads server, Toad Bot, the bank bot and the officers’ Google Drive',
    rows: [
      {
        tier: 'visitor',
        can: [{ text: 'Apply to raid', permission: 'apply' }, { text: 'A private interview room with the officers' }]
      },
      {
        tier: 'raider',
        can: [
          { text: 'Next raid from Discord events' },
          { text: 'Officer posts on the hub' },
          { text: 'Your role for the night from the officers’ Drive sheet' },
          { text: 'Submit highlight reels', permission: 'submit_highlight' },
          { text: 'Upload screenshots', permission: 'upload_screenshots' }
        ]
      },
      {
        tier: 'officer',
        can: [
          { text: 'Curate posts both ways', permission: 'manage_posts' },
          { text: 'Review highlights and spotlights', permission: 'manage_highlights' },
          { text: 'Interview rooms and recruiting needs', permission: 'manage_recruitment' },
          { text: 'Write the strategy and role sheets in Google Drive' }
        ]
      },
      {
        tier: 'admin',
        can: [{ text: 'Bots, their tokens and the site bridge' }, { text: 'Settings from the admin guide' }]
      }
    ]
  }
];

export function rank(tier: Tier): number {
  return TIERS.indexOf(tier);
}

export function unlocked(row: Row, viewer: Tier): boolean {
  return rank(row.tier) <= rank(viewer);
}

/**
 * The viewer's tier from the hub session. A member with no raid-night role still counts as a raider here: they can
 * browse raids and the bank, and the page says what a raid role adds.
 */
export function tierOf(session: Session | null | undefined): Tier {
  if (!session) return 'visitor';
  if (session.super_admin) return 'admin';
  if (session.global_officer || session.officer_days.length) return 'officer';
  return 'raider';
}

/** One line under the heading that says where the viewer stands. */
export function standing(tier: Tier): string {
  switch (tier) {
    case 'visitor':
      return 'You are not signed in. Everything is listed so you can see what joining gets you.';
    case 'raider':
      return 'The three apps are yours. What officers and super admins have is shown dimmed, with who holds it.';
    case 'officer':
      return 'You have everything raiders do, plus your raid night’s bank, curation and insights.';
    case 'admin':
      return 'Everything is unlocked. Changes made as the break-glass admin are shown and audited.';
  }
}

/** How a member gets more than they have. */
export const MORE: readonly { title: string; body: string }[] = [
  {
    title: 'Trial to raider',
    body: 'Your raid night’s officers promote you in Discord, and the hub follows at your next sign-in.'
  },
  { title: 'Bank helper', body: 'An officer gives you a token. Redeem it on the Bank page or with /bank redeem.' },
  { title: 'Officer', body: 'A Discord role for each raid night. Global officers cover both nights.' }
];
