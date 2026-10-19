/**
 * Which toad goes with whom. The artwork lives in static/logos/ (see the contact sheet at /logos/): a toad per class,
 * per role and per rank, each as a standalone toad and as a badge with its name. Every member gets the toads of what
 * the hub knows about them: their rank (officers and the Archtoad), their class and their role.
 */
import type { Tier } from './access';
import type { Role } from './mock/data';

export type ToadKind = 'rank' | 'class' | 'role';

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

/** Officers and super admins get the officer toad. */
const RANK_TOAD: Partial<Record<Tier, { id: string; label: string }>> = {
  officer: { id: 'ranks/officer', label: 'Officer' },
  admin: { id: 'ranks/officer', label: 'Officer' }
};

/**
 * The Archtoad is the guild master and leader, and belongs to one person: the Discord account `_gallagher`. The hub's
 * session carries the name the member shows in the server, so it is matched on that, ignoring case and a leading @.
 * (If the nickname ever differs, expose the Discord username on the session and match that instead.)
 */
export const ARCHTOAD_DISCORD_NAME = '_gallagher';

export function isArchtoad(name: string | null | undefined): boolean {
  return (name ?? '').trim().replace(/^@/, '').toLowerCase() === ARCHTOAD_DISCORD_NAME;
}

/** Jobs a member does for the guild; each has its own toad. */
export type Title = 'banker' | 'developer';

const TITLE_TOAD: Record<Title, { id: string; label: string }> = {
  banker: { id: 'ranks/banker', label: 'Banker' },
  developer: { id: 'ranks/developer', label: 'Developer' }
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

/** The Archtoad for the guild master, otherwise the officer toad for officers and admins. */
export function rankToad(tier: Tier, name?: string | null): Toad | null {
  if (isArchtoad(name)) return { kind: 'rank', id: 'ranks/archtoad', label: 'Archtoad' };
  const t = RANK_TOAD[tier];
  return t ? { kind: 'rank', ...t } : null;
}

export interface MemberFacts {
  tier?: Tier;
  /** The name the member shows in the server; picks out the Archtoad. */
  name?: string | null;
  titles?: readonly Title[];
  className?: string | null;
  role?: Role | null;
}

/**
 * The toads a member earns, rank first, then any guild jobs: an officer banker who plays a Priest healer gets Officer,
 * Banker, Priest and Healer.
 */
export function memberToads({ tier = 'raider', name, titles = [], className, role }: MemberFacts): Toad[] {
  return [rankToad(tier, name), ...titles.map(titleToad), classToad(className), roleToad(role)].filter(
    (t): t is Toad => t !== null
  );
}

/** Path of a toad's artwork under the site's base: the standalone toad, or the badge with its name. */
export function toadSrc(base: string, toad: Pick<Toad, 'id'>, badge = false): string {
  return `${base}/logos/${toad.id}${badge ? '-badge' : ''}.svg`;
}
