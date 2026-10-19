/**
 * Hub features: what each tier can do in the three apps a Toads member gets (the raid analyzer, the guild bank and
 * Discord with the officers' Google Drive). It mirrors the hub's RBAC table (services/api/src/toads_api/rbac/
 * permissions.py), and access.test.ts fails if a permission named here is missing there or sits in another tier. The
 * page only explains; every route still checks its own permission.
 */
import type { Session } from './api';

export type Tier = 'visitor' | 'raider' | 'officer' | 'admin';

export const TIERS: readonly Tier[] = ['visitor', 'raider', 'officer', 'admin'];

/** The tiers the Hub features page lists; super admins see it as officers do. */
export type FeatureTier = Exclude<Tier, 'admin'>;
export const FEATURE_TIERS: readonly FeatureTier[] = ['visitor', 'raider', 'officer'];

export const TIER_LABEL: Record<Tier, string> = {
  visitor: 'Visitor',
  raider: 'Raider',
  officer: 'Officer',
  admin: 'Super admin'
};

/** Shown on a row the viewer has not unlocked: who holds it, or how to get it. */
export const LOCKED: Record<FeatureTier, string> = {
  visitor: 'Open to everyone',
  raider: 'Log in with Discord to unlock',
  officer: 'For the officers of each raid night'
};

/** The column heading for each tier on the Hub features page. */
export const FEATURE_LABEL: Record<FeatureTier, string> = {
  visitor: 'Everyone',
  raider: 'Raiders',
  officer: 'Officers'
};

export interface Capability {
  text: string;
  /** The hub permission behind it (its value in permissions.py); none for public pages or things outside the hub. */
  permission?: string;
}

export interface Row {
  tier: FeatureTier;
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
    where: 'The hub, the Windows app and the command line',
    rows: [
      {
        tier: 'visitor',
        can: [{ text: 'Progression and clear times' }, { text: 'How we raid, with guild totals' }]
      },
      {
        tier: 'raider',
        can: [
          { text: 'Guild raid totals and week-on-week charts on the hub', permission: 'view_guild_raids' },
          { text: 'Your role number against the guild median', permission: 'view_own_performance' },
          { text: 'Your badges and the next tier', permission: 'view_own_performance' },
          { text: 'Claim your characters', permission: 'claim_character' },
          { text: 'Tell your officers which raid nights you will miss', permission: 'report_absence' },
          { text: 'Use your own Warcraft Logs key' },
          { text: 'Set your primary and secondary spec for the officers’ comps' },
          { text: 'Install the Windows app' }
        ]
      },
      {
        tier: 'officer',
        can: [
          { text: 'Anyone’s numbers and the roster’s badges', permission: 'view_others' },
          { text: 'Reference raid comparisons', permission: 'view_insights' },
          { text: 'Sync logs and set roles', permission: 'sync_logs' },
          { text: 'Approve character claims', permission: 'approve_claims' },
          { text: 'Build and lock in raid comps from your night’s roster', permission: 'build_comps' },
          { text: 'Your raid night’s absences in one place', permission: 'view_absences' },
          { text: 'Your raid night’s task board: assign tasks and set due dates', permission: 'manage_officer_board' },
          { text: 'Give members their award toads (global officers)', permission: 'manage_awards' }
        ]
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
          { text: 'Redeem a bank helper token to help run the bank' }
        ]
      },
      {
        tier: 'officer',
        can: [
          { text: 'Run your night’s request queue', permission: 'manage_bank' },
          { text: 'Import bank snapshots from the addon', permission: 'import_bank_snapshot' }
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
      }
    ]
  }
];

export function rank(tier: Tier): number {
  return TIERS.indexOf(tier);
}

/** The tier the Hub features page shows a viewer as: super admins as officers. */
export function featureTier(tier: Tier): FeatureTier {
  return tier === 'admin' ? 'officer' : tier;
}

export function unlocked(row: Row, viewer: Tier): boolean {
  return rank(row.tier) <= rank(viewer);
}

/** A signed-in member's best raid-night role; officers count as raiders. */
export type RaidRole = 'member' | 'trial' | 'raider';

/**
 * What a trial and a raider role hold beyond a plain member, from `_TRIAL` and `_RAIDER` in permissions.py
 * (access.test.ts checks them). The raider tier groups all three, so these say which of its rows need a raid role.
 */
export const RAID_ROLE_PERMISSIONS: Record<Exclude<RaidRole, 'member'>, readonly string[]> = {
  trial: ['view_own_performance', 'claim_character', 'report_absence'],
  raider: ['view_own_performance', 'claim_character', 'report_absence', 'upload_screenshots', 'submit_highlight']
};

export function raidRoleOf(session: Session | null | undefined): RaidRole {
  const roles = Object.values(session?.day_roles ?? {});
  if (session?.global_officer || roles.some((r) => r === 'raider' || r === 'officer')) return 'raider';
  return roles.includes('trial') ? 'trial' : 'member';
}

/** The raid role a capability needs on top of the raider tier, or null when every member has it. */
export function needsRole(c: Capability): Exclude<RaidRole, 'member'> | null {
  if (!c.permission) return null;
  if (RAID_ROLE_PERMISSIONS.trial.includes(c.permission)) return 'trial';
  return RAID_ROLE_PERMISSIONS.raider.includes(c.permission) ? 'raider' : null;
}

/** Whether a viewer holding `role` has a capability in a row they have unlocked. */
export function held(c: Capability, role: RaidRole): boolean {
  const needs = needsRole(c);
  return !needs || role === 'raider' || (role === 'trial' && needs === 'trial');
}

/**
 * The viewer's tier from the hub session. A member with no raid-night role still counts as a raider here: they can
 * browse raids and the bank, and the page marks the rows that need a trial or raider role (`held`).
 */
export function tierOf(session: Session | null | undefined): Tier {
  if (!session) return 'visitor';
  if (session.super_admin) return 'admin';
  if (session.global_officer || session.officer_days.length) return 'officer';
  return 'raider';
}

/** One line under the heading that says where the viewer stands. */
export function standing(tier: Tier): string {
  switch (featureTier(tier)) {
    case 'visitor':
      return 'You are not signed in. Everything is listed so you can see what joining gets you.';
    case 'raider':
      return 'The raider column is yours. What officers hold is shown dimmed.';
    case 'officer':
      return 'You have everything raiders do, plus your raid night’s bank, curation and insights.';
  }
}
