/**
 * Members' awards (docs/awards.md): the milestone, achievement and title toads global officers give members. The hub
 * stores who holds what; the artwork and names come from milestones.ts (milestones and achievements) and toads.ts
 * (titles). services/api/tests/test_awards.py fails if the hub's catalogue and these drift apart.
 */
import { call, ApiError, type Fetch, type MemberEntry } from './api';
import { MILESTONES } from './milestones';
import type { Title } from './toads';

export type AwardKind = 'milestone' | 'achievement' | 'title';

/** An award as the hub returns it. */
export interface AwardOut {
  id: number;
  award_id: string;
  name: string;
  kind: AwardKind;
  member_id: number;
  member_name: string;
  /** "YYYY-MM" for Raider of the Month, null for every other award. */
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
  /** The artwork under static/logos/, without `.svg`. */
  file: string;
}

/** Everything an officer can give, in the order the desk lists it. */
export const AWARDABLE: readonly Awardable[] = [
  ...MILESTONES.map((m) => ({
    id: m.id,
    name: m.name,
    kind: (m.file.startsWith('milestones/') ? 'milestone' : 'achievement') as AwardKind,
    monthly: m.id === 'raider-of-the-month',
    file: m.file
  })),
  ...TITLE_AWARDS.map((t) => ({
    id: t.id,
    name: t.name,
    kind: 'title' as AwardKind,
    monthly: false,
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
