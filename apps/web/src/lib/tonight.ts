/**
 * The top of a raid night's officer section: the next night, who will miss it with the role they play, and what that
 * leaves short. Built from the night's absences and its comp roster, which the page already reads.
 */
import type { Absence, TeamAbsences } from './absences';
import { specLabel, specOf, type PoolEntry, type Role } from './comp';

export interface AwayRaider {
  name: string;
  note: string | null;
  /** "Restoration Shaman"; "" until they set their specs on Me, or when they are not on the roster. */
  spec: string;
  role: Role | null;
  /** Whether the night's roster lists them, so "no specs set" is only said of someone it lists. */
  onRoster: boolean;
}

export interface Tonight {
  date: string;
  away: AwayRaider[];
  /** How many on the night's roster, so "3 of 24 away" reads at a glance; 0 when the roster did not load. */
  roster: number;
  /** Away players by role, roles with nobody away left out. */
  short: { role: Role; count: number }[];
  /** Away players whose role is not known (no spec set, or not on the roster), so `short` leaves them out. */
  unknown: number;
}

const ROLE_ORDER: Role[] = ['tank', 'healer', 'melee', 'ranged'];

export function tonight(team: TeamAbsences, pool: readonly PoolEntry[]): Tonight | null {
  const next = team.nights[0];
  if (!next) return null;
  const byId = new Map(pool.map((p) => [p.member_id, p]));
  const byName = new Map(pool.map((p) => [p.name.toLowerCase(), p]));
  const away = next.absent.map((a: Absence): AwayRaider => {
    const p = byId.get(a.member_id) ?? byName.get((a.member_name ?? '').toLowerCase());
    return {
      name: a.member_name || 'A member',
      note: a.note,
      spec: specLabel(p?.primary),
      role: specOf(p?.primary)?.role ?? null,
      onRoster: !!p
    };
  });
  const short = ROLE_ORDER.map((role) => ({ role, count: away.filter((a) => a.role === role).length })).filter(
    (r) => r.count > 0
  );
  return { date: next.date, away, roster: pool.length, short, unknown: away.filter((a) => a.role === null).length };
}
