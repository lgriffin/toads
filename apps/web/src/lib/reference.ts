/**
 * Reference comparison: officers compare one of the guild's raids with another guild's "reference" raid.
 * Importing a reference needs the hub's dedicated Warcraft Logs login (one shared account any officer connects).
 * The worker does the Warcraft Logs work, so every write returns a queued job and the page polls the overview.
 * Shapes mirror services/api (`/api/days/{day}/reference`); comparison displays arrive formatted by wcl-core.
 */

import { ApiError, call, type Fetch, type Session } from './api';
import { mmss } from './format';

// --- API shapes ------------------------------------------------------------------------------------

export type LoginStatus = 'working' | 'expired';

export interface ReferenceLogin {
  /** False when the hub has no Warcraft Logs app (client id and secret) configured. */
  configured: boolean;
  connected: boolean;
  status: LoginStatus | null;
  connected_by: string | null;
  connected_at: string | null;
}

export interface StoredRaid {
  report_id: string;
  title: string;
  /** "YYYY-MM-DD HH:MM:SS" */
  raid_date: string;
  zone: string | null;
  raid_size: number | null;
  label: string | null;
  owner: string | null;
}

export interface BuiltComparison {
  guild_report: string;
  reference_report: string;
  guild_title: string;
  reference_title: string;
  generated_at: string;
}

export type JobKind = 'import' | 'compare' | 'label' | 'delete';
export type JobStatus = 'queued' | 'running' | 'done' | 'failed';

export interface ReferenceJob {
  id: string;
  kind: JobKind;
  status: JobStatus;
  message: string;
  report: string;
  created_at: string;
  updated_at: string;
}

export interface ReferenceOverview {
  login: ReferenceLogin;
  /** When the worker last listed the stored raids; null means never. */
  generated_at: string | null;
  /** Other guilds' raids, newest first. */
  references: StoredRaid[];
  /** The guild's own raids, newest first. */
  guild_raids: StoredRaid[];
  comparisons: BuiltComparison[];
  /** The newest ten. */
  jobs: ReferenceJob[];
}

export interface ComparedRaid {
  report_id: string;
  title: string;
  raid_date: string;
  zone: string | null;
  raid_size: number | null;
  duration_ms: number | null;
}

export interface Metric {
  key: string;
  label: string;
  guild: number | null;
  reference: number | null;
  guild_display: string;
  reference_display: string;
  delta_percent: number | null;
  higher_is_better: boolean;
  /** True is good for the guild, false is bad, null is neutral. */
  better: boolean | null;
}

export interface ClassRow {
  player_class: string;
  role: string;
  metric: string;
  guild_count: number;
  guild_average: number | null;
  reference_count: number;
  reference_average: number | null;
  delta_percent: number | null;
}

export interface ConsumableRow {
  name: string;
  guild_uses: number;
  guild_users: number;
  reference_uses: number;
  reference_users: number;
}

export interface EncounterRow {
  name: string;
  guild_duration_ms: number | null;
  reference_duration_ms: number | null;
  guild_damage: number | null;
  reference_damage: number | null;
  guild_healing: number | null;
  reference_healing: number | null;
  duration_delta_percent: number | null;
}

export interface ComparisonScope {
  /** True when the guild raid covered more bosses and the per-boss sections use only the shared ones. */
  scoped: boolean;
  shared_encounters: number;
  guild_extra_encounters: string[];
}

export const COMPARISON_VERSION = 1;

export interface Comparison {
  version: number;
  guild: ComparedRaid;
  reference: ComparedRaid;
  scope: ComparisonScope;
  overview: Metric[];
  composition: Metric[];
  classes: ClassRow[];
  consumables: ConsumableRow[];
  encounters: EncounterRow[];
}

export interface ComparisonResponse {
  generated_at: string;
  comparison: Comparison;
}

// --- client ----------------------------------------------------------------------------------------

const root = (day: string) => `/api/days/${encodeURIComponent(day)}/reference`;
const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

export const getReferenceOverview = (day: string, f: Fetch = fetch) => call<ReferenceOverview>(f, root(day));

/** Starts the Warcraft Logs login; send the browser to `authorize_url`. */
export const startReferenceLogin = (day: string, f: Fetch = fetch) =>
  call<{ authorize_url: string }>(f, `${root(day)}/login`, { method: 'POST' });

export const disconnectReferenceLogin = (day: string, f: Fetch = fetch) =>
  call<void>(f, `${root(day)}/login`, { method: 'DELETE' });

/** `report` is a report code or a Warcraft Logs report URL. */
export const importReference = (day: string, report: string, label: string | null, f: Fetch = fetch) =>
  call<ReferenceJob>(f, `${root(day)}/imports`, { method: 'POST', ...json({ report, label }) });

export const requestComparison = (day: string, guildReport: string, referenceReport: string, f: Fetch = fetch) =>
  call<ReferenceJob>(f, `${root(day)}/comparisons`, {
    method: 'POST',
    ...json({ guild_report: guildReport, reference_report: referenceReport })
  });

/** A built comparison, or null when the worker has not built it (yet). */
export async function getComparison(
  day: string,
  guildReport: string,
  referenceReport: string,
  f: Fetch = fetch
): Promise<ComparisonResponse | null> {
  const path = `${root(day)}/comparisons/${encodeURIComponent(guildReport)}/${encodeURIComponent(referenceReport)}`;
  try {
    return await call<ComparisonResponse>(f, path);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

export const setReferenceLabel = (day: string, report: string, label: string | null, f: Fetch = fetch) =>
  call<ReferenceJob>(f, `${root(day)}/references/${encodeURIComponent(report)}/label`, {
    method: 'PUT',
    ...json({ label })
  });

export const deleteReference = (day: string, report: string, f: Fetch = fetch) =>
  call<ReferenceJob>(f, `${root(day)}/references/${encodeURIComponent(report)}`, { method: 'DELETE' });

/** What to tell an officer when a reference call fails. */
export function referenceError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Your session ended; sign in again.';
    case 403:
      return 'Reference comparisons are for officers of this raid day.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}

// --- helpers ---------------------------------------------------------------------------------------

/**
 * The raid day the page works on: the requested one when the member may use it, else their first officer day
 * (every day for a global officer), else null for a non-officer. The API checks the day again on every call.
 */
export function pickDay(
  session: Pick<Session, 'officer_days' | 'raid_days' | 'global_officer'>,
  requested?: string | null
): string | null {
  if (requested && (session.global_officer || session.officer_days.includes(requested))) return requested;
  if (session.officer_days.length) return session.officer_days[0];
  if (session.global_officer) return session.raid_days[0] ?? null;
  return null;
}

/** "2026-09-21 · Gruul's Lair (Gruul's Lair, 25-man) [EU speed clear]" for a raid picker. */
export function raidLabel(r: StoredRaid): string {
  const details = [r.zone, r.raid_size ? `${r.raid_size}-man` : null].filter(Boolean).join(', ');
  return [raidDay(r.raid_date), '·', r.title, details ? `(${details})` : '', r.label ? `[${r.label}]` : '']
    .filter(Boolean)
    .join(' ');
}

/** The date part of a stored raid's "YYYY-MM-DD HH:MM:SS". */
export const raidDay = (raidDate: string) => raidDate.slice(0, 10);

export const isPending = (j: Pick<ReferenceJob, 'status'>) => j.status === 'queued' || j.status === 'running';

/** True while the worker still has something to do, so the page keeps polling. */
export const hasPendingJobs = (jobs: Pick<ReferenceJob, 'status'>[]) => jobs.some(isPending);

/** "+12.5%", "−3.0%", "0.0%", or "—" when there is nothing to compare. */
export function formatDelta(percent: number | null | undefined): string {
  if (percent === null || percent === undefined || !Number.isFinite(percent)) return '—';
  const rounded = Math.round(percent * 10) / 10;
  if (rounded === 0) return '0.0%';
  return `${rounded > 0 ? '+' : '−'}${Math.abs(rounded).toFixed(1)}%`;
}

export type Tone = 'positive' | 'negative' | 'neutral';

export function metricTone(m: Pick<Metric, 'better'>): Tone {
  return m.better === true ? 'positive' : m.better === false ? 'negative' : 'neutral';
}

/** The tone of a raw difference: positive when it favours the guild. */
export function deltaTone(percent: number | null | undefined, higherIsBetter = true): Tone {
  if (percent === null || percent === undefined || !Number.isFinite(percent) || Math.round(percent * 10) === 0) {
    return 'neutral';
  }
  return percent > 0 === higherIsBetter ? 'positive' : 'negative';
}

/** Screen-reader words for a tone, since colour alone must not carry it. */
export const TONE_WORDS: Record<Tone, string> = { positive: 'better', negative: 'worse', neutral: '' };

/** m:ss for a duration in milliseconds; "—" when unknown. Hours roll into minutes (e.g. "95:04"). */
export function durationLabel(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms) || ms < 0) return '—';
  return mmss(Math.round(ms / 1000));
}

/** "1.2M", "845.3k", "950"; "—" when unknown. For encounter totals, which arrive raw. */
export function compactNumber(n: number | null | undefined): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return '—';
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(Math.round(n));
}

export function averageLabel(n: number | null | undefined): string {
  return n === null || n === undefined || !Number.isFinite(n) ? '—' : Math.round(n).toLocaleString('en-GB');
}

export const JOB_KIND_LABELS: Record<JobKind, string> = {
  import: 'Import',
  compare: 'Compare',
  label: 'Relabel',
  delete: 'Delete'
};

export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  queued: 'Queued',
  running: 'Running',
  done: 'Done',
  failed: 'Failed'
};

/** One line on the state of the shared Warcraft Logs login. */
export function loginLabel(login: ReferenceLogin): string {
  if (!login.configured) return 'This hub has no Warcraft Logs app configured, so references cannot be imported.';
  if (!login.connected) return 'Not connected. An officer connects the guild’s Warcraft Logs account once for everyone.';
  if (login.status === 'expired') return 'The login has expired. Reconnect to import more references.';
  return 'Connected and working.';
}

/** The one-line notice for `?login=ok|failed` after Warcraft Logs sends the browser back. */
export function loginNotice(param: string | null | undefined): string {
  if (param === 'ok') return 'Warcraft Logs login connected.';
  if (param === 'failed') return 'Warcraft Logs did not complete the login. Try connecting again.';
  return '';
}

/** Warcraft Logs report codes are 16 letters and digits. */
const CODE = /^[A-Za-z0-9]{16}$/;
const URL_CODE = /^https?:\/\/(?:[a-z]+\.)?warcraftlogs\.com\/reports\/([A-Za-z0-9]{16})(?:[/?#]|$)/;

/** The report code in a pasted code or Warcraft Logs URL, or null when it holds none. The API checks it again. */
export function reportCode(input: string): string | null {
  const s = input.trim();
  if (CODE.test(s)) return s;
  return URL_CODE.exec(s)?.[1] ?? null;
}

/** The note shown when the comparison only uses the bosses both raids fought. */
export function scopeNote(scope: ComparisonScope): string {
  if (!scope.scoped) return '';
  const extra = scope.guild_extra_encounters;
  const bosses = scope.shared_encounters === 1 ? 'boss' : 'bosses';
  const tail = extra.length ? ` Not counted: ${extra.join(', ')}.` : '';
  return `Consumables and encounters cover only the ${scope.shared_encounters} shared ${bosses}.${tail}`;
}

export const comparisonKey = (guildReport: string, referenceReport: string) => `${guildReport}/${referenceReport}`;

/** "3h 16m" or "48m" for a whole raid's length; "—" when unknown. */
export function raidLength(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms) || ms < 0) return '—';
  const minutes = Math.round(ms / 60_000);
  const h = Math.floor(minutes / 60);
  return h ? `${h}h ${minutes % 60}m` : `${minutes}m`;
}

/** The raid's zone, size and duration as one line for the comparison header. */
export function comparedRaidLine(r: ComparedRaid): string {
  return [
    raidDay(r.raid_date),
    r.zone,
    r.raid_size ? `${r.raid_size}-man` : null,
    r.duration_ms !== null ? raidLength(r.duration_ms) : null
  ]
    .filter(Boolean)
    .join(' · ');
}

/**
 * What the reference page can do. The live page calls the API; the preview changes sample data. Each resolves true
 * when the request was accepted, so the view can clear its form; failures are reported by the host.
 */
export interface ReferenceActions {
  connect(): Promise<boolean>;
  disconnect(): Promise<boolean>;
  importReport(report: string, label: string | null): Promise<boolean>;
  relabel(report: string, label: string | null): Promise<boolean>;
  remove(report: string): Promise<boolean>;
  compare(guildReport: string, referenceReport: string): Promise<boolean>;
  open(guildReport: string, referenceReport: string): Promise<boolean>;
}
