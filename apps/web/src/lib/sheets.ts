/**
 * Raid totals from the guild's CBA and RPB spreadsheets. Shapes mirror services/api toads_api/raid_sheets
 * (summary.py and schemas.py); every number can be null when a sheet tab is missing or reads oddly.
 * Sheet text is untrusted: render it as text, never as HTML.
 */
import { ApiError } from './api';

export type PlayerRole = 'tank' | 'healer' | 'caster' | 'physical';

export interface ClearTime {
  /** As the sheet's title abbreviates it, e.g. "BT". */
  zone: string;
  seconds: number;
}

/** One raid's totals: a point on the home page's week-by-week trend. */
export interface RaidHeadline {
  raid_day: string;
  /** ISO date, e.g. "2026-09-23". */
  raid_date: string;
  title: string | null;
  zone: string | null;
  report_code: string | null;
  log_valid: boolean | null;
  characters: number | null;
  clear_times: ClearTime[];
  /** 0-1: the raid's average consumable uptime on bosses. */
  consumables_avg: number | null;
  /** Players under 80% consumable uptime. */
  low_consumables: string[];
  gear_issues: number | null;
  players_with_gear_issues: number | null;
  drums: number | null;
  potions: number | null;
  interrupts: number | null;
  deaths: number | null;
  avoidable_damage: number | null;
}

export interface PlayerLine {
  name: string;
  role: PlayerRole | null;
  /** 0-1 */
  consumables: number | null;
  gear_issues: number | null;
  drums: number | null;
  potions: number | null;
  interrupts: number | null;
  deaths: number | null;
  avoidable_damage: number | null;
}

export interface RaidSummary {
  headline: RaidHeadline;
  players: PlayerLine[];
}

export interface SheetLink {
  snapshot_id: number;
  kind: 'cba' | 'rpb';
  title: string;
  tab: string;
  url: string;
  fetched_at: string;
}

/** The sheets attached to one raid, without their rows. */
export interface RaidSheets {
  raid_day: string;
  raid_date: string;
  report_code: string | null;
  sheets: SheetLink[];
}

export const DASH = '—';
/** Players under this share of consumable uptime are listed by name (matches LOW_CONSUMABLES in summary.py). */
export const LOW_CONSUMABLES = 0.8;

const isNum = (n: number | null | undefined): n is number => typeof n === 'number' && Number.isFinite(n);

/** 6512 -> "1:48:32", 59 -> "0:00:59"; "—" for null, negative or non-finite. */
export function clearTime(seconds: number | null | undefined): string {
  if (!isNum(seconds) || seconds < 0) return DASH;
  const s = Math.round(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${h}:${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

/** "BT 1:48:32 · MH 1:08:40", or "—" when the title had none. */
export function clearTimes(times: ClearTime[] | null | undefined): string {
  if (!times?.length) return DASH;
  return times.map((t) => `${t.zone} ${clearTime(t.seconds)}`).join(' · ');
}

/** 1234567 -> "1,234,567"; "—" for null. */
export function count(n: number | null | undefined): string {
  return isNum(n) ? Math.round(n).toLocaleString('en-GB') : DASH;
}

/** 0.9372 -> "94%"; "—" for null. */
export function percent(fraction: number | null | undefined, digits = 0): string {
  return isNum(fraction) ? `${(fraction * 100).toFixed(digits)}%` : DASH;
}

/** "40 across 21 players", "0", or "—". */
export function gearLabel(h: Pick<RaidHeadline, 'gear_issues' | 'players_with_gear_issues'>): string {
  if (!isNum(h.gear_issues)) return DASH;
  const players = h.players_with_gear_issues;
  if (h.gear_issues === 0 || !isNum(players)) return count(h.gear_issues);
  return `${count(h.gear_issues)} across ${count(players)} player${players === 1 ? '' : 's'}`;
}

const REPORT_CODE = /^[A-Za-z0-9]{16}$/;

/** The Warcraft Logs report link, only for a well-formed report code. */
export function reportUrl(code: string | null | undefined): string | null {
  return code && REPORT_CODE.test(code) ? `https://classic.warcraftlogs.com/reports/${code}` : null;
}

export type Tone = 'better' | 'worse' | 'same';

export interface Change {
  delta: number;
  /** "down 12", "up 3 pts", "same" */
  label: string;
  tone: Tone;
}

export interface ChangeOptions {
  /** Deaths, avoidable damage and gear issues: fewer is better. */
  lowerIsBetter?: boolean;
  /** Formats the size of the change; whole numbers by default. */
  format?: (abs: number) => string;
}

/** How a number moved since the previous raid; null when either side is missing. */
export function change(
  current: number | null | undefined,
  previous: number | null | undefined,
  { lowerIsBetter = true, format = count }: ChangeOptions = {}
): Change | null {
  if (!isNum(current) || !isNum(previous)) return null;
  const delta = current - previous;
  const size = format(Math.abs(delta));
  if (Math.abs(delta) < 1e-9 || /^0(\D|$)/.test(size)) return { delta: 0, label: 'same', tone: 'same' };
  const down = delta < 0;
  return { delta, label: `${down ? 'down' : 'up'} ${size}`, tone: down === lowerIsBetter ? 'better' : 'worse' };
}

/** Percentage points, for changes in a 0-1 share: 0.03 -> "3 pts". */
export const points = (abs: number) => `${Math.round(abs * 100)} pt${Math.round(abs * 100) === 1 ? '' : 's'}`;

/** Newest first; the API already sorts this way, but the page should not depend on it. */
export function newestFirst(raids: RaidHeadline[]): RaidHeadline[] {
  return [...raids].sort((a, b) => (a.raid_date < b.raid_date ? 1 : a.raid_date > b.raid_date ? -1 : 0));
}

/** The raid to compare `raid` with: the one before it on the same raid day. */
export function previousRaid(raids: RaidHeadline[], raid: RaidHeadline): RaidHeadline | null {
  return newestFirst(raids).find((r) => r.raid_day === raid.raid_day && r.raid_date < raid.raid_date) ?? null;
}

/** What to tell a member when a raid sheet call fails. */
export function sheetsError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Raid totals could not be loaded; try again.';
  if (e.status === 401) return 'Sign in with Discord to see raid totals.';
  if (e.status === 403) return 'Raid totals are for members with a role on a raid day.';
  if (e.status >= 500) return 'Raid totals are unavailable right now; try again shortly.';
  return e.message || 'Raid totals could not be loaded; try again.';
}
