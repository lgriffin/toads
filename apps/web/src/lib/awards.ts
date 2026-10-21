/**
 * Members' awards (docs/awards.md): the milestone, achievement, title and weekly honour toads global officers give
 * members. The hub stores who holds what; the artwork and names come from milestones.ts (milestones, achievements and
 * honours) and toads.ts (titles). services/api/tests/test_awards.py fails if the hub's catalogue and these drift apart.
 */
import { call, ApiError, type Fetch, type MemberEntry } from './api';
import { MILESTONES } from './milestones';
import type { Title } from './toads';

export type AwardKind = 'milestone' | 'achievement' | 'title' | 'honour';

/** An award as the hub returns it. */
export interface AwardOut {
  id: number;
  award_id: string;
  name: string;
  kind: AwardKind;
  member_id: number;
  member_name: string;
  /** "YYYY-MM" for Raider of the Month, "YYYY-Www" for a weekly honour, null for every other award. */
  period: string | null;
  note: string | null;
  awarded_at: string;
}

export interface AwardIn {
  member_id: number;
  award_id: string;
  period?: string;
  note?: string;
}

export const myAwards = (f: Fetch = fetch) => call<AwardOut[]>(f, '/api/me/awards');
export const guildAwards = (f: Fetch = fetch) => call<AwardOut[]>(f, '/api/awards');
export const giveAward = (body: AwardIn, f: Fetch = fetch) =>
  call<AwardOut>(f, '/api/admin/awards', {
    method: 'POST',
    body: JSON.stringify(body)
  });
export const takeBackAward = (id: number, f: Fetch = fetch) =>
  call<void>(f, `/api/admin/awards/${encodeURIComponent(id)}`, {
    method: 'DELETE'
  });

/** Titles are jobs a member does for the guild; their toads sit with the rank toad. */
export const TITLE_AWARDS: readonly {
  id: Title;
  name: string;
  blurb: string;
}[] = [
  { id: 'banker', name: 'Banker', blurb: 'Keeps the guild bank.' },
  { id: 'developer', name: 'Developer', blurb: 'Builds and keeps the hub.' },
  {
    id: 'discord-admin',
    name: 'Discord Admin',
    blurb: 'Keeps the Discord server in order.'
  }
];

export interface Awardable {
  id: string;
  name: string;
  kind: AwardKind;
  /** Given for a month and held once per month (Raider of the Month). */
  monthly: boolean;
  /** Given for a raid week and held once per week (Raider of the Week, Sunder King and the other honours). */
  weekly: boolean;
  /** The artwork under static/logos/, without `.svg`. */
  file: string;
}

/** Everything an officer can give, in the order the desk lists it. */
export const AWARDABLE: readonly Awardable[] = [
  ...MILESTONES.map((m) => ({
    id: m.id,
    name: m.name,
    kind: (m.category === 'honours'
      ? 'honour'
      : m.file.startsWith('milestones/')
        ? 'milestone'
        : 'achievement') as AwardKind,
    monthly: m.id === 'raider-of-the-month',
    weekly: m.category === 'honours',
    file: m.file
  })),
  ...TITLE_AWARDS.map((t) => ({
    id: t.id,
    name: t.name,
    kind: 'title' as AwardKind,
    monthly: false,
    weekly: false,
    file: `ranks/${t.id}`
  }))
];

const BY_ID = new Map(AWARDABLE.map((a) => [a.id, a]));

export function awardable(id: string): Awardable | undefined {
  return BY_ID.get(id);
}

/** The titles among a member's awards, for their member toads. */
export function titlesOf(awards: readonly Pick<AwardOut, 'award_id' | 'kind'>[]): Title[] {
  const ids = new Set(awards.filter((a) => a.kind === 'title').map((a) => a.award_id));
  return TITLE_AWARDS.map((t) => t.id).filter((id) => ids.has(id));
}

/** "2026-09" -> "September 2026". */
export function monthLabel(period: string): string {
  const [y, m] = period.split('-').map(Number);
  if (!y || !m) return period;
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString('en-GB', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC'
  });
}

/** The Monday that starts an ISO week ("2026-W43"), or null for anything else. */
function weekStart(period: string): Date | null {
  const m = /^(\d{4})-W(\d{2})$/.exec(period);
  if (!m) return null;
  const [y, w] = [Number(m[1]), Number(m[2])];
  // Week 1 is the week with 4 January in it.
  const jan4 = new Date(Date.UTC(y, 0, 4));
  const monday = new Date(jan4);
  monday.setUTCDate(4 - ((jan4.getUTCDay() + 6) % 7) + (w - 1) * 7);
  return monday;
}

/** A date's ISO week, "2026-W43": what the awards desk gives a weekly honour for by default. */
export function isoWeek(day: Date): string {
  const d = new Date(Date.UTC(day.getFullYear(), day.getMonth(), day.getDate()));
  // The Thursday of the same week decides the year.
  d.setUTCDate(d.getUTCDate() + 3 - ((d.getUTCDay() + 6) % 7));
  const jan4 = new Date(Date.UTC(d.getUTCFullYear(), 0, 4));
  const days = (d.getTime() - jan4.getTime()) / 86400000;
  const week = 1 + Math.round((days - 3 + ((jan4.getUTCDay() + 6) % 7)) / 7);
  return `${d.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

/** An award's period for people: "September 2026" for a month, "week of 19 Oct 2026" for a raid week. */
export function periodLabel(period: string): string {
  const monday = weekStart(period);
  if (!monday) return monthLabel(period);
  return `week of ${monday.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })}`;
}

/** What to tell an officer when giving or taking back an award fails. */
export function awardError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  if (e.status === 401) return 'Sign in with Discord first.';
  if (e.status === 403) return 'Only global officers give awards.';
  return e.message || 'Something went wrong; try again.';
}

/** Where the awards desk reads and writes: the hub, or the preview's sample data. */
export interface AwardsBackend {
  wall(): Promise<AwardOut[]>;
  members(): Promise<MemberEntry[]>;
  give(body: AwardIn): Promise<AwardOut>;
  takeBack(id: number): Promise<void>;
}
