/**
 * Browser-side calls to the hub API (same origin behind Caddy; the session cookie is HttpOnly, so the
 * browser attaches it and scripts never see it). Shapes mirror services/api; regenerate types with
 * `npm run api:types` once the OpenAPI schema settles.
 */

import {
  highlightFromApi,
  postFromApi,
  type ApiHighlight,
  type ApiPost,
  type ApiStory,
  type DeskSummary
} from './community-api';
import type { MyBadges } from './badges';
import type { HomeLayout } from './home';
import type { AnalyzerPage } from './home-payload';
import type { NextRaidAnswer } from './next-raid';
import type { MyPerformance } from './performance';
import type { RaidHeadline, RaidSheets, RaidSummary } from './sheets';

export interface Session {
  member_id: number;
  display_name: string;
  global_officer: boolean;
  day_roles: Record<string, 'trial' | 'raider' | 'officer'>;
  /** Days the member holds a trial, raider or officer role on, in config order. */
  raid_days: string[];
  /** Days with officer powers; every day for a global officer. */
  officer_days: string[];
}

export interface MemberEntry {
  member_id: number;
  display_name: string;
  /** Officers only; a string because Discord ids exceed Number.MAX_SAFE_INTEGER. */
  discord_user_id: string | null;
}

export type ClaimStatus = 'pending' | 'approved' | 'rejected';

export interface Claim {
  id: number;
  member_id: number;
  character_id: number;
  character_name: string;
  raid_day_id: string | null;
  status: ClaimStatus;
  reason: string | null;
}

/** A non-2xx answer. Bank routes also carry ToadsBank's error `code`, `details` and `current` (docs/bank.md). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly code?: string,
    readonly details?: unknown,
    readonly current?: unknown
  ) {
    super(message);
  }
}

export type Fetch = typeof fetch;

/** One JSON call to the API; a non-2xx answer throws `ApiError` carrying the API's `detail` (and `error`, if any). */
export async function call<T>(f: Fetch, path: string, init: RequestInit = {}): Promise<T> {
  const extra = (init.headers ?? {}) as Record<string, string>;
  const r = await f(path, {
    credentials: 'same-origin',
    ...init,
    headers: { accept: 'application/json', ...(init.body ? { 'content-type': 'application/json' } : {}), ...extra }
  });
  if (!r.ok) {
    let detail = r.statusText;
    let error: { code?: unknown; details?: unknown; current?: unknown } | undefined;
    try {
      const body = await r.json();
      if (typeof body?.detail === 'string') detail = body.detail;
      if (body?.error && typeof body.error === 'object') error = body.error;
    } catch {
      // non-JSON error body; keep the status text
    }
    const code = typeof error?.code === 'string' ? error.code : undefined;
    throw new ApiError(r.status, detail, code, error?.details, error?.current);
  }
  return (r.status === 204 ? undefined : await r.json()) as T;
}

/** The signed-in member, or null when nobody is signed in. */
export async function getSession(f: Fetch = fetch): Promise<Session | null> {
  try {
    return await call<Session>(f, '/api/session');
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return null;
    throw e;
  }
}

export const listMembers = (f: Fetch = fetch) => call<MemberEntry[]>(f, '/api/members');

export const listClaims = (f: Fetch = fetch) => call<Claim[]>(f, '/api/claims');

export const createClaim = (characterId: number, f: Fetch = fetch) =>
  call<Claim>(f, '/api/claims', { method: 'POST', body: JSON.stringify({ character_id: characterId }) });

export const unclaim = (claimId: number, f: Fetch = fetch) =>
  call<void>(f, `/api/claims/${encodeURIComponent(claimId)}`, { method: 'DELETE' });

/** What to tell a member when a claim call fails. */
export function claimError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Sign in with Discord to claim characters.';
    case 403:
      return 'Claiming needs a trial or raider role on a raid day.';
    case 404:
      return 'No character with that id has appeared in the guild’s logs.';
    case 409:
      return 'Someone already holds or is waiting on that character. Ask an officer if it is yours.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}

export function statusLabel(c: Pick<Claim, 'status' | 'reason'>): string {
  if (c.status === 'approved') return 'Approved';
  if (c.status === 'pending') return 'Waiting for an officer';
  return c.reason ? `Rejected: ${c.reason}` : 'Rejected';
}

// --- the member's own settings -------------------------------------------------------------------

export type NameSource = 'discord' | 'character';

export interface NameOption {
  source: NameSource;
  name: string;
  character_id: number | null;
}

export type WclKeyStatus = 'unverified' | 'working' | 'rejected';

/** A saved Warcraft Logs key as the API describes it. The id and secret themselves never come back. */
export interface WclKey {
  client_id_hint: string;
  status: WclKeyStatus;
  updated_at: string;
  checked_at: string | null;
}

export interface AccountSettings {
  shown_name: string;
  name_source: NameSource;
  name_character_id: number | null;
  /** The Discord nickname first, then the member's approved characters. */
  name_options: NameOption[];
  wcl_key: WclKey | null;
  /** Which key the member's Warcraft Logs requests use right now. */
  wcl_key_in_use: 'own' | 'guild';
}

export const getAccountSettings = (f: Fetch = fetch) => call<AccountSettings>(f, '/api/me/settings');

export const chooseName = (option: Pick<NameOption, 'source' | 'character_id'>, f: Fetch = fetch) =>
  call<AccountSettings>(f, '/api/me/name', {
    method: 'PUT',
    body: JSON.stringify({ source: option.source, character_id: option.character_id })
  });

export const saveWclKey = (clientId: string, clientSecret: string, f: Fetch = fetch) =>
  call<AccountSettings>(f, '/api/me/wcl-key', {
    method: 'PUT',
    body: JSON.stringify({ client_id: clientId, client_secret: clientSecret })
  });

export const removeWclKey = (f: Fetch = fetch) => call<AccountSettings>(f, '/api/me/wcl-key', { method: 'DELETE' });

export function wclKeyLabel(s: Pick<AccountSettings, 'wcl_key'>): string {
  if (!s.wcl_key) return 'Not set: your requests use the guild key.';
  const which = `Key ending ${s.wcl_key.client_id_hint}`;
  switch (s.wcl_key.status) {
    case 'working':
      return `${which}: working, and used for your requests.`;
    case 'rejected':
      return `${which}: Warcraft Logs refused it, so your requests use the guild key. Save a new one to fix it.`;
    default:
      return `${which}: saved, and checked the next time it is used.`;
  }
}

/** What to tell a member when a settings call fails. */
export function settingsError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  if (e.status === 401) return 'Sign in with Discord to change your settings.';
  return e.message || 'Something went wrong; try again.';
}

// --- raid totals from the CBA and RPB sheets -------------------------------------------------------

function dayQuery(day?: string, limit?: number): string {
  const q = new URLSearchParams();
  if (day) q.set('day', day);
  if (limit !== undefined) q.set('limit', String(limit));
  const qs = q.toString();
  return qs ? `?${qs}` : '';
}

/** Each recent raid's sheet totals, newest first; all raid days unless `day` is given. */
export function raidTrend(day?: string, limit?: number, f: Fetch = fetch): Promise<RaidHeadline[]> {
  return call<RaidHeadline[]>(f, `/api/raid-sheets/trend${dayQuery(day, limit)}`);
}

/** One raid's totals and per-player lines. `date` is an ISO date. */
export const raidSummary = (day: string, date: string, f: Fetch = fetch) =>
  call<RaidSummary>(f, `/api/days/${encodeURIComponent(day)}/raids/${encodeURIComponent(date)}/sheets/summary`);

/** The latest raids with sheets attached, newest first; all raid days unless `day` is given. */
export function recentRaidSheets(day?: string, limit?: number, f: Fetch = fetch): Promise<RaidSheets[]> {
  return call<RaidSheets[]>(f, `/api/raid-sheets/recent${dayQuery(day, limit)}`);
}

// --- the member's customisable hub home ------------------------------------------------------------

export type { HomeLayout, HomeWidget, WidgetId } from './home';

export const getHome = (f: Fetch = fetch) => call<HomeLayout>(f, '/api/me/home');

/** Show exactly `shown`, in that order; every other widget stays placeable, hidden. */
export const saveHome = (shown: string[], f: Fetch = fetch) =>
  call<HomeLayout>(f, '/api/me/home', { method: 'PUT', body: JSON.stringify({ shown }) });

export const resetHome = (f: Fetch = fetch) => call<HomeLayout>(f, '/api/me/home', { method: 'DELETE' });

/** The analyzer's widgets (guild-wide), as the worker last built them. */
export const analyzerHome = (f: Fetch = fetch) => call<AnalyzerPage>(f, '/api/home/analyzer');

/** The next raid: the soonest Discord scheduled event, else the raid days' usual start time. */
export const nextRaid = (f: Fetch = fetch) => call<NextRaidAnswer>(f, '/api/home/next-raid');

/** The member's main character in the last raid against the guild median for their role. */
export const myPerformance = (f: Fetch = fetch) => call<MyPerformance>(f, '/api/me/performance');

/** The member's main character's Toads badges, earned or not. */
export const myBadges = (f: Fetch = fetch) => call<MyBadges>(f, '/api/me/badges');

/** What to tell a member when saving their home fails. */
export function homeError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  if (e.status === 401) return 'Sign in with Discord to change your home.';
  if (e.status === 403) return 'Only officers can place that widget.';
  return e.message || 'Something went wrong; try again.';
}

// --- community reads the hub home uses -------------------------------------------------------------

export const postsFeed = async (f: Fetch = fetch) => (await call<ApiPost[]>(f, '/api/posts')).map(postFromApi);

export const guildHighlights = async (f: Fetch = fetch) =>
  (await call<ApiHighlight[]>(f, '/api/highlights')).map(highlightFromApi);

export const publicStory = (f: Fetch = fetch) => call<ApiStory>(f, '/api/public/story');

export const deskSummary = (f: Fetch = fetch) => call<DeskSummary>(f, '/api/desk');
