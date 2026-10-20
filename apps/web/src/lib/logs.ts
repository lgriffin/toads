/**
 * Logs (docs/logs.md): every analysed guild raid with the desktop app's raid analysis, filtered by the weekday it was
 * raided on. The worker builds the pages with the analyzer's RaidPageService (guides/raid_pages.md in
 * lgriffin/warcraftlogs_project); the API decides who sees per-player numbers. This module shapes the calls and does
 * the filtering and boss-history sums the page shows.
 */
import { ApiError, analyzerHome, call, type Fetch, type Session } from './api';
import type { AnalyzerPage } from './home-payload';
import { RAID_NIGHTS } from './nights';

/** One raid in the list (the analyzer's RaidSummary). */
export interface RaidSummary {
  report_id: string;
  title: string;
  zone: string;
  /** "YYYY-MM-DD HH:MM:SS", the raid's local start. */
  raid_date: string;
  /** 0 for Monday to 6 for Sunday; null when the date could not be read. */
  weekday: number | null;
  size: number;
  url: string;
}

export interface RaidRow {
  summary: RaidSummary;
  analysed: boolean;
  /** Open the full analysis under this raid day; null opens it guild-wide. */
  day: string | null;
  /** The viewer sees per-player numbers for this raid. */
  full: boolean;
}

export interface BossPlayer {
  name: string;
  player_class: string;
  role: string;
  kills: number;
  damage: number;
  healing: number;
  damage_taken: number;
}

export interface BossDay {
  kills: number;
  duration_ms: number;
  damage: number;
  healing: number;
  /** Only on weekdays the viewer sees in full. */
  players?: BossPlayer[];
}

export interface BossHistory {
  encounter_id: number;
  name: string;
  /** Keyed by weekday ("0" is Monday). */
  days: Record<string, BossDay>;
}

export interface LogsOverview {
  generated_at: string | null;
  raids: RaidRow[];
  bosses: BossHistory[];
  /** Weekdays whose per-player numbers the viewer sees; null for every weekday. */
  full_weekdays: number[] | null;
}

export interface Player {
  name: string;
  player_class: string;
}

export interface EncounterPlayer extends Player {
  role: string;
  damage: number;
  healing: number;
  damage_taken: number;
  active_percent: number;
}

export interface Encounter {
  encounter_id: number;
  name: string;
  duration_ms: number;
  damage: number;
  healing: number;
  players?: EncounterPlayer[];
}

export interface Uptime {
  spell_name: string;
  fight_name: string;
  uptime_percent: number;
}

/** The analyzer's RaidPage: one raid's analysis, a section per tab of the desktop raid view. */
export interface RaidPage {
  version: number;
  summary: RaidSummary;
  duration_ms: number;
  warnings: string[];
  composition: Record<'tanks' | 'healers' | 'melee' | 'ranged', Player[]>;
  healers: (Player & {
    healing: number;
    overhealing: number;
    overheal_percent: number;
    dispels: number;
    active_percent: number;
  })[];
  tanks: (Player & { damage_taken: number; mitigated: number; mitigation_percent: number; active_percent: number })[];
  melee: (Player & { damage: number; active_percent: number })[];
  ranged: (Player & { damage: number; active_percent: number })[];
  consumable_names: string[];
  consumables: { name: string; role: string; counts: Record<string, number> }[];
  boss_vs_trash: { name: string; boss: number; trash: number }[];
  interrupts: (Player & { spell_name: string; count: number })[];
  cancelled_casts: (Player & {
    total_casts: number;
    cancelled_casts: number;
    cancel_rate: number;
    spells: { spell_name: string; total_casts: number; cancelled_casts: number; cancel_rate: number }[];
  })[];
  debuff_uptimes: Uptime[];
  totem_uptimes: Uptime[];
  engineering: {
    name: string;
    total_casts: number;
    total_damage: number;
    users: number;
    min_avg: number;
    median_avg: number;
    max_avg: number;
  }[];
  encounters: Encounter[];
}

/** What every signed-in member sees of a raid: its size by role and each boss's totals, nobody's own numbers. */
export interface RaidOverview {
  version: number;
  summary: RaidSummary;
  duration_ms: number;
  composition_counts: Record<'tanks' | 'healers' | 'melee' | 'ranged', number>;
  encounters: Encounter[];
}

export type RaidView = { full: true; page: RaidPage } | { full: false; page: RaidOverview };

export const getLogs = (f: Fetch = fetch) => call<LogsOverview>(f, '/api/logs');
export const getRaid = (report: string, day: string | null, f: Fetch = fetch) =>
  call<RaidView>(
    f,
    day
      ? `/api/days/${encodeURIComponent(day)}/logs/${encodeURIComponent(report)}`
      : `/api/logs/${encodeURIComponent(report)}`
  );

/** The analyzer's home widgets built from one raid night's raids only (GET /api/home/nights/{day}). */
export const getNightPage = (day: string, f: Fetch = fetch) =>
  call<AnalyzerPage>(f, `/api/home/nights/${encodeURIComponent(day)}`);

/** Where the Logs pages read from: the hub, or the preview's sample data. */
export interface LogsBackend {
  overview(): Promise<LogsOverview>;
  raid(report: string, day: string | null): Promise<RaidView>;
  /** The analyzer's widgets for one raid night, or for every raid when `night` is null. */
  widgets(night: string | null): Promise<AnalyzerPage>;
}

export const hubLogs: LogsBackend = {
  overview: () => getLogs(),
  raid: (report, day) => getRaid(report, day),
  widgets: (night) => (night ? getNightPage(night) : analyzerHome())
};

/** A raid night the Logs page can open on. */
export interface LogNight {
  id: string;
  name: string;
  /** 0 is Monday; null when the night's name carries no weekday. */
  weekday: number | null;
}

/** The guild's raid nights in config order: the session's `day_names`, else the nights the web app knows. */
export function logNights(dayNames: Record<string, string> | undefined): LogNight[] {
  const named = dayNames && Object.keys(dayNames).length ? Object.entries(dayNames) : RAID_NIGHTS.map((n) => [n.id, n.name]);
  return named.map(([id, name]) => ({ id, name, weekday: weekdayNamed(name) }));
}

/** The weekday a raid day's name says when it names exactly one ("Wednesday", "Wed raid"), as the API reads it. */
export function weekdayNamed(name: string): number | null {
  const words = new Set(name.toLowerCase().split(/[^a-z]+/));
  const hits = WEEKDAYS.filter((w) => words.has(w.name.toLowerCase()) || words.has(w.short.toLowerCase()));
  return hits.length === 1 ? hits[0].day : null;
}

/**
 * The night Logs opens on: the raid night of the viewer's Toad badge. Super admins and global officers see every
 * night, and a member with no night or with several opens on every raid (null).
 */
export function defaultNight(
  session: Pick<Session, 'raid_days' | 'global_officer' | 'super_admin'>,
  nights: readonly LogNight[]
): string | null {
  if (session.super_admin || session.global_officer) return null;
  const mine = nights.filter((n) => session.raid_days.includes(n.id));
  return mine.length === 1 ? mine[0].id : null;
}

export function logsError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  if (e.status === 401) return 'Sign in with Discord first.';
  if (e.status === 404) return 'This raid has not been analysed yet. The hub picks new raids up within the hour.';
  return e.message || 'Something went wrong; try again.';
}

/** Monday first, as the analyzer numbers them (0 is Monday). */
export const WEEKDAYS = [
  { day: 0, short: 'Mon', name: 'Monday' },
  { day: 1, short: 'Tue', name: 'Tuesday' },
  { day: 2, short: 'Wed', name: 'Wednesday' },
  { day: 3, short: 'Thu', name: 'Thursday' },
  { day: 4, short: 'Fri', name: 'Friday' },
  { day: 5, short: 'Sat', name: 'Saturday' },
  { day: 6, short: 'Sun', name: 'Sunday' }
] as const;

export function weekdayName(day: number | null): string {
  return day === null ? 'Unknown day' : (WEEKDAYS[day]?.name ?? 'Unknown day');
}

export interface LogFilter {
  /** The weekdays to show; empty shows every day. */
  weekdays: number[];
  /** A zone, or '' for every zone. */
  zone: string;
  /** Matched against the title and the zone, any case. */
  query: string;
}

export const EVERYTHING: LogFilter = { weekdays: [], zone: '', query: '' };

export function filterRaids(rows: RaidRow[], f: LogFilter): RaidRow[] {
  const q = f.query.trim().toLowerCase();
  return rows.filter((r) => {
    const s = r.summary;
    if (f.weekdays.length && (s.weekday === null || !f.weekdays.includes(s.weekday))) return false;
    if (f.zone && s.zone !== f.zone) return false;
    return !q || s.title.toLowerCase().includes(q) || s.zone.toLowerCase().includes(q);
  });
}

/** Each weekday's raid count, for the chips. */
export function raidsPerWeekday(rows: RaidRow[]): number[] {
  const counts = [0, 0, 0, 0, 0, 0, 0];
  for (const r of rows) if (r.summary.weekday !== null) counts[r.summary.weekday] += 1;
  return counts;
}

export function zonesOf(rows: RaidRow[]): string[] {
  return [...new Set(rows.map((r) => r.summary.zone).filter(Boolean))].sort();
}

/** Add a weekday to the selection, or take it out. */
export function toggleWeekday(selected: number[], day: number): number[] {
  return selected.includes(day) ? selected.filter((d) => d !== day) : [...selected, day].sort((a, b) => a - b);
}

/** Per second over the given milliseconds; 0 when there is no time. */
export function perSecond(amount: number, ms: number): number {
  return ms > 0 ? amount / (ms / 1000) : 0;
}

export interface BossPlayerSum extends BossPlayer {
  /** Average damage and healing per kill. */
  damage_per_kill: number;
  healing_per_kill: number;
}

export interface BossSum {
  encounter_id: number;
  name: string;
  kills: number;
  /** Average kill time. */
  duration_ms: number;
  /** The raid's damage and healing per second, over every kill. */
  dps: number;
  hps: number;
  /** Per-player totals over the shown weekdays; null when the viewer sees none of them in full. */
  players: BossPlayerSum[] | null;
  /** Some shown weekdays' players are left out (the viewer is not their officer). */
  partial: boolean;
}

/** One boss's history over the shown weekdays (every weekday when none is picked). */
export function sumBoss(boss: BossHistory, weekdays: number[]): BossSum | null {
  const days = Object.entries(boss.days).filter(([d]) => !weekdays.length || weekdays.includes(Number(d)));
  const kills = days.reduce((n, [, d]) => n + d.kills, 0);
  if (!kills) return null;
  const duration = days.reduce((n, [, d]) => n + d.duration_ms, 0);
  const seen = days.filter(([, d]) => d.players !== undefined);
  const players = new Map<string, BossPlayer>();
  for (const [, d] of seen) {
    for (const p of d.players ?? []) {
      // One row per character and role, as the analyzer keeps a respec apart.
      const key = `${p.name}|${p.role}`;
      const mine = players.get(key) ?? { ...p, kills: 0, damage: 0, healing: 0, damage_taken: 0 };
      mine.kills += p.kills;
      mine.damage += p.damage;
      mine.healing += p.healing;
      mine.damage_taken += p.damage_taken;
      players.set(key, mine);
    }
  }
  return {
    encounter_id: boss.encounter_id,
    name: boss.name,
    kills,
    duration_ms: Math.round(duration / kills),
    dps: perSecond(days.reduce((n, [, d]) => n + d.damage, 0), duration),
    hps: perSecond(days.reduce((n, [, d]) => n + d.healing, 0), duration),
    players: seen.length
      ? [...players.values()]
          .map((p) => ({ ...p, damage_per_kill: p.damage / p.kills, healing_per_kill: p.healing / p.kills }))
          .sort((a, b) => b.damage_per_kill - a.damage_per_kill || a.name.localeCompare(b.name))
      : null,
    partial: seen.length > 0 && seen.length < days.length
  };
}

/** The boss history over the shown weekdays, most kills first. */
export function bossHistory(bosses: BossHistory[], weekdays: number[]): BossSum[] {
  return bosses
    .map((b) => sumBoss(b, weekdays))
    .filter((b): b is BossSum => b !== null)
    .sort((a, b) => b.kills - a.kills || a.name.localeCompare(b.name));
}

/** The desktop raid view's tabs, in its order; which a page has depends on what the raid logged. */
export const RAID_TABS = [
  { id: 'encounters', label: 'Encounters' },
  { id: 'composition', label: 'Composition' },
  { id: 'healers', label: 'Healers' },
  { id: 'tanks', label: 'Tanks' },
  { id: 'melee', label: 'Melee' },
  { id: 'ranged', label: 'Ranged' },
  { id: 'consumables', label: 'Consumables' },
  { id: 'boss_vs_trash', label: 'Boss vs trash' },
  { id: 'interrupts', label: 'Interrupts' },
  { id: 'cancelled_casts', label: 'Cast efficiency' },
  { id: 'debuff_uptimes', label: 'Debuff uptime' },
  { id: 'totem_uptimes', label: 'Totem uptime' },
  { id: 'engineering', label: 'Engineering' }
] as const;

export type RaidTab = (typeof RAID_TABS)[number]['id'];

/** The tabs this raid has anything to show on. */
export function tabsFor(page: RaidPage): RaidTab[] {
  return RAID_TABS.map((t) => t.id).filter((id) => {
    if (id === 'composition') return Object.values(page.composition ?? {}).some((p) => p.length);
    const rows = page[id] as unknown[] | undefined;
    return Array.isArray(rows) && rows.length > 0;
  });
}

/** "2h 05m" or "42m"; "—" when unknown. */
export function raidLength(ms: number | null | undefined): string {
  if (!ms || ms < 0) return '—';
  const minutes = Math.round(ms / 60_000);
  const h = Math.floor(minutes / 60);
  return h ? `${h}h ${String(minutes % 60).padStart(2, '0')}m` : `${minutes}m`;
}

/** The raid's date as the list shows it, read as written (the analyzer's local start). */
export function raidDateLabel(s: RaidSummary): string {
  const [date] = s.raid_date.split(' ');
  const parsed = new Date(`${date}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return s.raid_date || '—';
  return parsed.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}
