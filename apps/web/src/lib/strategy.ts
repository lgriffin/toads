/**
 * Raid strategy docs (docs/strategy.md): one pinned Google Doc per classic raid, and the raid each night is running, so
 * the night's Raid page shows that raid's doc. Officers keep the docs in Google Drive; the hub only links them.
 *
 * - GET    /api/strategy                  every raid's pinned doc and the docs it replaced, and each night's raid
 * - POST   /api/admin/strategy            pin a doc to a raid, replacing its pinned doc (global officers)
 * - DELETE /api/admin/strategy/{id}       take a doc down; the one it replaced is pinned again
 * - POST   /api/days/{day}/strategy/docs  the same, as one of that night's officers (every officer may pin)
 * - DELETE /api/days/{day}/strategy/docs/{id}
 * - GET    /api/days/{day}/strategy       the night's raid and its pinned doc (the Raid page)
 * - PUT    /api/days/{day}/strategy       say which raid the night is running (that night's officers)
 */
import { ApiError, call, type Fetch } from './api';

export const TITLE_LIMIT = 80;
export const URL_LIMIT = 500;

export interface Raid {
  id: string;
  short: string;
  name: string;
}

export interface StrategyDoc {
  id: number;
  raid: string;
  title: string;
  url: string;
  /** Who pinned it, by the name they chose on the hub; null once they are gone. */
  added_by: string | null;
  added_at: string;
}

export interface RaidStrategy {
  raid: Raid;
  pinned: StrategyDoc | null;
  /** The docs the pinned one replaced, newest first. */
  replaced: StrategyDoc[];
}

export interface NightRaid {
  raid_day: string;
  name: string;
  raid: string | null;
}

export interface Library {
  raids: RaidStrategy[];
  nights: NightRaid[];
}

export interface NightStrategy {
  raid_day: string;
  raid: Raid | null;
  pinned: StrategyDoc | null;
}

export interface StrategyBackend {
  library(): Promise<Library>;
  /** `day`: the night the officer pins through; null for global officers and super admins. */
  pin(raid: string, url: string, title: string, day: string | null): Promise<StrategyDoc>;
  remove(id: number, day: string | null): Promise<void>;
  night(day: string): Promise<NightStrategy>;
  setNight(day: string, raid: string | null): Promise<NightStrategy>;
}

const night = (day: string) => `/api/days/${encodeURIComponent(day)}/strategy`;
const docs = (day: string | null) => (day === null ? '/api/admin/strategy' : `${night(day)}/docs`);

export function hubStrategy(f: Fetch = fetch): StrategyBackend {
  return {
    library: () => call<Library>(f, '/api/strategy'),
    pin: (raid, url, title, day) =>
      call<StrategyDoc>(f, docs(day), { method: 'POST', body: JSON.stringify({ raid, url, title }) }),
    remove: (id, day) => call<void>(f, `${docs(day)}/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    night: (day) => call<NightStrategy>(f, night(day)),
    setNight: (day, raid) => call<NightStrategy>(f, night(day), { method: 'PUT', body: JSON.stringify({ raid }) })
  };
}

const GOOGLE_HOSTS = new Set(['docs.google.com', 'drive.google.com']);

/** The API's own check, so the form can say what is wrong before sending: an https Google Docs or Drive link. */
export function docProblem(url: string, title = ''): string | null {
  if (title.trim().length > TITLE_LIMIT) return `Keep the name to ${TITLE_LIMIT} characters.`;
  const text = url.trim();
  if (!text) return 'Paste the Google Doc’s link.';
  try {
    const u = new URL(text);
    if (u.protocol !== 'https:' || !GOOGLE_HOSTS.has(u.hostname) || u.username || u.password) throw new Error('host');
    if (text.length > URL_LIMIT || /\s/.test(text)) throw new Error('shape');
  } catch {
    return 'Paste the doc’s https://docs.google.com or drive.google.com link.';
  }
  return null;
}

/** "Pinned 22 Oct by Hopscotch". */
export function pinnedLine(doc: Pick<StrategyDoc, 'added_at' | 'added_by'>): string {
  const when = new Date(doc.added_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  return doc.added_by ? `Pinned ${when} by ${doc.added_by}` : `Pinned ${when}`;
}

export function strategyError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  if (e.status === 403) return 'Only officers pin strategy docs, and only a night’s officers pick its raid.';
  if (e.status === 404) return 'That doc is gone; someone may have taken it down.';
  return e.message || 'Something went wrong; try again.';
}
