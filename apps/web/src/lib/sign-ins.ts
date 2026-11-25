/**
 * The officers' sign-in audit (docs/sign-ins.md): for a day the officer picks, who signed in to the hub and when, and
 * when each member last signed in. Each raid night's officers see their own night's members, from
 * /api/days/{day}/sign-ins; the global tier also sees members on no raid night, from /api/admin/sign-ins. Days run
 * midnight to midnight in the guild's time zone. This module only shapes the calls and the labels.
 */
import { ApiError, call, type Fetch } from './api';

export interface SignInEntry {
  member_id: number;
  member_name: string;
  /** ISO time with offset. */
  at: string;
}

export interface LastSignIn {
  member_id: number;
  member_name: string;
  /** Null: they have never signed in (the hub knows them from their Discord roles). */
  last_signed_in_at: string | null;
}

export interface DayCount {
  date: string;
  sign_ins: number;
  members: number;
}

export interface SignInDay {
  raid_day: string | null;
  date: string;
  /** That day's sign-ins, newest first. */
  sign_ins: SignInEntry[];
  /** Everyone in the view, most recently signed in first; those who never have come last. */
  members: LastSignIn[];
  /** The 14 days up to the chosen one, newest first. */
  recent: DayCount[];
}

/** Where the audit reads from: the hub, or the preview's sample sign-ins. `day` null is members on no raid night. */
export interface SignInsBackend {
  day(day: string | null, on?: string): Promise<SignInDay>;
}

const path = (day: string | null) =>
  day === null ? '/api/admin/sign-ins' : `/api/days/${encodeURIComponent(day)}/sign-ins`;

export function hubSignIns(f: Fetch = fetch): SignInsBackend {
  return {
    day: (day, on) => call<SignInDay>(f, on ? `${path(day)}?on=${encodeURIComponent(on)}` : path(day))
  };
}

/** `YYYY-MM-DD` of a local date. */
export function isoDay(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/** The day `n` days after `day` (negative for before), as `YYYY-MM-DD`. */
export function shiftDay(day: string, n: number): string {
  const [y, m, d] = day.split('-').map(Number);
  return isoDay(new Date(y, m - 1, d + n));
}

/** "Tue 24 Nov": the label a day carries in the audit. */
export function dayLabel(day: string): string {
  const [y, m, d] = day.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
}

/** "19:42": the time of a sign-in, in the reader's own clock. */
export function timeLabel(at: string): string {
  return new Date(at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

/** How long ago a last sign-in was, in words: "Today", "Yesterday", "3 days ago", "5 weeks ago", or "Never". */
export function sinceLabel(at: string | null, now: Date = new Date()): string {
  if (!at) return 'Never';
  const then = new Date(at);
  const days = Math.round(
    (new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime() -
      new Date(then.getFullYear(), then.getMonth(), then.getDate()).getTime()) /
      86_400_000
  );
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 14) return `${days} days ago`;
  if (days < 70) return `${Math.floor(days / 7)} weeks ago`;
  return `${Math.floor(days / 30)} months ago`;
}

/** True when a member has not signed in for `days` days or more (or ever), so the list can mark who has gone quiet. */
export function quiet(at: string | null, days = 14, now: Date = new Date()): boolean {
  return !at || now.getTime() - new Date(at).getTime() >= days * 86_400_000;
}

/** What to tell the officer when a read fails. */
export function signInError(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 403) return 'Only this raid night’s officers can see its sign-ins.';
    if (e.status === 422) return e.message || 'That day cannot be shown.';
  }
  return 'The sign-ins could not be loaded. Try again shortly.';
}
