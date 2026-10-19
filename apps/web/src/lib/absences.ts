/**
 * Absences (docs/absences.md): a raid day's trials and raiders say which raid nights they will miss on the Calendar
 * page, and that day's officers see the team's upcoming absences in one place (the Calendar and the Raid page). The
 * API decides who may report for which team and who may see a team's list; this module only shapes the calls and
 * the month grid.
 */
import { ApiError, call, type Fetch, type Session } from './api';

export interface Absence {
  id: number;
  member_id: number;
  member_name: string;
  raid_day: string;
  /** ISO dates, both included. */
  first_date: string;
  last_date: string;
  note: string | null;
  /** The raid nights it covers from today on, as ISO dates. */
  nights: string[];
}

export interface TeamNight {
  date: string;
  absent: Absence[];
}

export interface TeamAbsences {
  raid_day: string;
  nights: TeamNight[];
  absences: Absence[];
}

export interface AbsenceIn {
  first_date: string;
  last_date?: string;
  note?: string;
}

export const NOTE_LIMIT = 200;

export const myAbsences = (f: Fetch = fetch) => call<Absence[]>(f, '/api/me/absences');
export const reportAbsence = (day: string, body: AbsenceIn, f: Fetch = fetch) =>
  call<Absence>(f, `/api/days/${encodeURIComponent(day)}/absences`, { method: 'POST', body: JSON.stringify(body) });
export const cancelAbsence = (id: number, f: Fetch = fetch) =>
  call<void>(f, `/api/me/absences/${encodeURIComponent(id)}`, { method: 'DELETE' });
export const teamAbsences = (day: string, f: Fetch = fetch) =>
  call<TeamAbsences>(f, `/api/days/${encodeURIComponent(day)}/absences`);

/** Where the calendar reads and writes: the hub, or the preview's sample data. */
export interface AbsencesBackend {
  mine(): Promise<Absence[]>;
  report(day: string, body: AbsenceIn): Promise<Absence>;
  cancel(id: number): Promise<void>;
  team(day: string): Promise<TeamAbsences>;
}

export const hubAbsences: AbsencesBackend = {
  mine: () => myAbsences(),
  report: (day, body) => reportAbsence(day, body),
  cancel: (id) => cancelAbsence(id),
  team: (day) => teamAbsences(day)
};

export function absenceError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  if (e.status === 401) return 'Sign in with Discord first.';
  if (e.status === 403) return 'You can only do that for a raid team you are on.';
  return e.message || 'Something went wrong; try again.';
}

/** Who sees which raid days, as the page and its switcher need them. */
export interface RaidDays {
  /** Days the viewer may open on the Raid page, in config order. */
  days: string[];
  /** Days the viewer reports absences for: the teams they hold a trial, raider or officer role on. */
  teams: string[];
  /** Days the viewer runs as an officer (every day for a global officer or super admin). */
  officerDays: string[];
  /** Each day's name by id. */
  names: Record<string, string>;
}

/** Each day's name: from the hub, or the id title-cased for an older hub that sends none. */
export function dayName(id: string, names: Record<string, string> = {}): string {
  return names[id] ?? (id === 'wed' ? 'Wednesday' : id === 'sun' ? 'Sunday' : id.charAt(0).toUpperCase() + id.slice(1));
}

/**
 * Members see their own team's night (both, in the rare case they are on both teams); officers see the nights they
 * run; super admins and global officers see every night and switch between them.
 */
export function raidDaysOf(session: Pick<Session, 'raid_days' | 'officer_days' | 'day_names'> | null | undefined): RaidDays {
  if (!session) return { days: [], teams: [], officerDays: [], names: {} };
  const names = session.day_names ?? {};
  const order = Object.keys(names);
  const seen = new Set([...session.raid_days, ...session.officer_days]);
  const days = order.length ? order.filter((d) => seen.has(d)) : [...seen];
  for (const d of seen) if (!days.includes(d)) days.push(d);
  return { days, teams: session.raid_days, officerDays: session.officer_days, names };
}

/** An ISO date (YYYY-MM-DD) for a local calendar date. */
export function isoDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function parse(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d);
}

/** "Wed 28 Oct", for an ISO date. */
export function nightLabel(iso: string): string {
  return parse(iso).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
}

/** "Wed 28 Oct" for one night, "Wed 28 Oct to Wed 4 Nov" for a run. */
export function rangeLabel(a: Pick<Absence, 'first_date' | 'last_date'>): string {
  return a.first_date === a.last_date ? nightLabel(a.first_date) : `${nightLabel(a.first_date)} to ${nightLabel(a.last_date)}`;
}

/** The weekday (0 is Sunday, as Date.getDay) each raid day falls on, from its name. */
export function weekdayOf(name: string): number | null {
  const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  const words = name.toLowerCase().match(/[a-z]+/g) ?? [];
  const hits = days.filter((d) => words.some((w) => w === d || w === d.slice(0, 3)));
  return hits.length === 1 ? days.indexOf(hits[0]) : null;
}

export interface CalendarDay {
  /** ISO date. */
  date: string;
  day: number;
  inMonth: boolean;
  past: boolean;
  /** The raid days whose night this is, among the viewer's teams. */
  raids: string[];
  /** The viewer's absences covering this date. */
  away: Absence[];
}

/** One month as weeks of seven days, Monday first, with the viewer's raid nights and absences marked. */
export function monthGrid(
  year: number,
  month: number,
  today: string,
  teams: { id: string; weekday: number | null }[],
  absences: Absence[]
): CalendarDay[][] {
  const first = new Date(year, month, 1);
  const start = new Date(year, month, 1 - ((first.getDay() + 6) % 7));
  const weeks: CalendarDay[][] = [];
  for (let w = 0; w < 6; w++) {
    const week: CalendarDay[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + w * 7 + i);
      const date = isoDate(d);
      week.push({
        date,
        day: d.getDate(),
        inMonth: d.getMonth() === month,
        past: date < today,
        raids: teams.filter((t) => t.weekday === d.getDay()).map((t) => t.id),
        away: absences.filter((a) => a.first_date <= date && date <= a.last_date)
      });
    }
    if (w >= 4 && week.every((d) => !d.inMonth)) break;
    weeks.push(week);
  }
  return weeks;
}
