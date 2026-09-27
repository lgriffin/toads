/**
 * Browser-side calls to the hub API (same origin behind Caddy; the session cookie is HttpOnly, so the
 * browser attaches it and scripts never see it). Shapes mirror services/api; regenerate types with
 * `npm run api:types` once the OpenAPI schema settles.
 */

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

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string
  ) {
    super(message);
  }
}

type Fetch = typeof fetch;

async function call<T>(f: Fetch, path: string, init: RequestInit = {}): Promise<T> {
  const r = await f(path, {
    credentials: 'same-origin',
    ...init,
    headers: { accept: 'application/json', ...(init.body ? { 'content-type': 'application/json' } : {}) }
  });
  if (!r.ok) {
    let detail = r.statusText;
    try {
      const body = await r.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      // non-JSON error body; keep the status text
    }
    throw new ApiError(r.status, detail);
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
