/**
 * Which toad goes with whom. The artwork lives in static/logos/ (see the contact sheet at /logos/): a toad per class,
 * per role and per rank, each as a standalone toad and as a badge with its name. Every member gets the toads of what
 * the hub knows about them: their rank (the Archtoad, super admin or officer) and the member toad, the badges their
 * Discord roles earn (role-badges.ts), their class and their role.
 */
import type { Tier } from './access';
import type { Role } from './mock/data';
import { roleBadge } from './role-badges';

export type ToadKind = 'rank' | 'day' | 'class' | 'role';

export interface Toad {
  kind: ToadKind;
  /** The file under static/logos/, without the extension: `classes/priest`, `roles/healer`, `ranks/officer`. */
  id: string;
  /** What the toad stands for, for the alt text and tooltip: Priest, Healer, Officer. */
  label: string;
}

const CLASS_IDS = ['druid', 'hunter', 'mage', 'paladin', 'priest', 'rogue', 'shaman', 'warlock', 'warrior'] as const;

/** The WoW class colours, as the badges use them. */
export const CLASS_COLOUR: Record<string, string> = {
  druid: '#FF7D0A',
  hunter: '#ABD473',
  mage: '#69CCF0',
  paladin: '#F58CBA',
  priest: '#FFFFFF',
  rogue: '#FFF569',
  shaman: '#0070DE',
  warlock: '#9482C9',
  warrior: '#C79C6E'
};

const ROLE_TOAD: Record<Role, { id: string; label: string }> = {
  Tank: { id: 'roles/tank', label: 'Tank' },
  Healer: { id: 'roles/healer', label: 'Healer' },
  Melee: { id: 'roles/damage', label: 'Damage' },
  Ranged: { id: 'roles/damage', label: 'Damage' }
};

/** Every signed-in member gets the member toad; officers the officer toad and super admins the super admin toad. */
const RANK_TOAD: Partial<Record<Tier, { id: string; label: string }>> = {
  raider: { id: 'ranks/member', label: 'Member' },
  officer: { id: 'ranks/officer', label: 'Officer' },
  admin: { id: 'ranks/super-admin', label: 'Super admin' }
};

const MEMBER_TOAD: Toad = { kind: 'rank', id: 'ranks/member', label: 'Member' };

/**
 * The Archtoad is the guild master and leader, and belongs to one person: the Discord account `_gallagher`. It is
 * matched on the Discord username the hub's session carries (never the server nickname, which members change often),
 * ignoring case and a leading @.
 */
export const ARCHTOAD_DISCORD_USERNAME = '_gallagher';

export function isArchtoad(username: string | null | undefined): boolean {
  return (username ?? '').trim().replace(/^@/, '').toLowerCase() === ARCHTOAD_DISCORD_USERNAME;
}

/** Jobs a member does for the guild; each has its own toad. */
export type Title = 'banker' | 'developer' | 'discord-admin';

const TITLE_TOAD: Record<Title, { id: string; label: string }> = {
  banker: { id: 'ranks/banker', label: 'Banker' },
  developer: { id: 'ranks/developer', label: 'Developer' },
  'discord-admin': { id: 'ranks/discord-admin', label: 'Discord Admin' }
};

export function titleToad(title: Title): Toad {
  return { kind: 'rank', ...TITLE_TOAD[title] };
}

export function classToad(className: string | null | undefined): Toad | null {
  const key = (className ?? '').trim().toLowerCase();
  if (!(CLASS_IDS as readonly string[]).includes(key)) return null;
  return { kind: 'class', id: `classes/${key}`, label: key[0].toUpperCase() + key.slice(1) };
}

export function roleToad(role: Role | null | undefined): Toad | null {
  const t = role ? ROLE_TOAD[role] : undefined;
  return t ? { kind: 'role', ...t } : null;
}

/**
 * A member's highest rank: the Archtoad for the guild master, the super admin toad for super admins, the officer toad
 * for officers and the member toad for everyone else signed in.
 */
export function rankToad(tier: Tier, username?: string | null): Toad | null {
  if (isArchtoad(username)) return { kind: 'rank', id: 'ranks/archtoad', label: 'Archtoad' };
  const t = RANK_TOAD[tier];
  return t ? { kind: 'rank', ...t } : null;
}

/** The toad for a badge a Discord role earns (role-badges.ts); null for an id the web app does not know. */
export function roleBadgeToad(id: string): Toad | null {
  const b = roleBadge(id);
  if (!b) return null;
  const kind: ToadKind = b.file.startsWith('days/') ? 'day' : b.file.startsWith('classes/') ? 'class' : 'role';
  return { kind, id: b.file, label: b.name };
}

export interface MemberFacts {
  tier?: Tier;
  /** The member's Discord username (not their nickname); picks out the Archtoad. */
  username?: string | null;
  titles?: readonly Title[];
  /** Badge ids their Discord roles earn (GET /api/me/role-badges). */
  roleBadges?: readonly string[];
  className?: string | null;
  role?: Role | null;
}

/**
 * The toads a member earns, rank first, then the member toad everyone signed in holds, any guild jobs, the badges their
 * Discord roles earn, their class and their role, each toad once: a super admin banker on the Wednesday role who plays
 * a Priest healer gets Super admin, Member, Banker, Wednesday Toad, Priest and Healer.
 */
export function memberToads({
  tier = 'raider',
  username,
  titles = [],
  roleBadges = [],
  className,
  role
}: MemberFacts): Toad[] {
  const rank = rankToad(tier, username);
  const all = [
    rank,
    rank ? MEMBER_TOAD : null,
    ...titles.map(titleToad),
    ...roleBadges.map(roleBadgeToad),
    classToad(className),
    roleToad(role)
  ];
  const seen = new Set<string>();
  return all.filter((t): t is Toad => t !== null && !seen.has(t.id) && !!seen.add(t.id));
}

/** Path of a toad's artwork under the site's base: the standalone toad, or the badge with its name. */
export function toadSrc(base: string, toad: Pick<Toad, 'id'>, badge = false): string {
  return `${base}/logos/${toad.id}${badge ? '-badge' : ''}.svg`;
}
