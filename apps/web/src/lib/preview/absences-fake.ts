/**
 * The preview's absences: sample data in the browser only, so the Calendar and the Raid page work on GitHub Pages with
 * no hub behind them. Dates are counted from today so the sample never goes stale; changes last until a reload.
 */
import { ApiError, type Session } from '$lib/api';
import { isoDate, weekdayOf, type Absence, type AbsenceIn, type AbsencesBackend, type TeamAbsences } from '$lib/absences';
import type { PreviewRole } from './gate';

export const PREVIEW_DAY_NAMES: Record<string, string> = { wed: 'Wednesday', sun: 'Sunday' };

/** The preview's raid days per view: Hopscotch raids Wednesday, leads it as an officer, or sees both as a super admin. */
export function previewRaidSession(role: PreviewRole | null): Pick<Session, 'raid_days' | 'officer_days' | 'day_names'> | null {
  if (role === null) return null;
  const officer_days = role === 'admin' ? ['wed', 'sun'] : role === 'officer' ? ['wed'] : [];
  return { raid_days: ['wed'], officer_days, day_names: PREVIEW_DAY_NAMES };
}

const ME = 1;

/** The `n`th night from today of a raid day (0 is the next one). */
function night(day: string, n: number): string {
  const weekday = weekdayOf(PREVIEW_DAY_NAMES[day]) ?? 0;
  const d = new Date();
  d.setDate(d.getDate() + ((weekday - d.getDay() + 7) % 7) + 7 * n);
  return isoDate(d);
}

function nightsOf(day: string, first: string, last: string): string[] {
  const out: string[] = [];
  for (let n = 0; n < 60; n++) {
    const d = night(day, n);
    if (d > last) break;
    if (d >= first) out.push(d);
  }
  return out;
}

const SEED: [number, string, string, number, number, string | null][] = [
  [ME, 'Hopscotch', 'wed', 2, 2, 'Family wedding.'],
  [2, 'Lilypadd', 'wed', 0, 0, 'Working late.'],
  [3, 'Ribbit', 'wed', 1, 3, 'Half-term holiday.'],
  [4, 'Croak', 'sun', 0, 1, 'Visiting family.'],
  [5, 'Bogwort', 'sun', 3, 3, 'Moving house.']
];

let rows: Absence[] = SEED.map(([member_id, member_name, raid_day, from, to, note], i) => {
  const first_date = night(raid_day, from);
  const last_date = night(raid_day, to);
  return { id: i + 1, member_id, member_name, raid_day, first_date, last_date, note, nights: nightsOf(raid_day, first_date, last_date) };
});

/** The same rules as the API, so the preview refuses what the hub would. */
function check(day: string, body: AbsenceIn, editing?: number): Pick<Absence, 'first_date' | 'last_date' | 'note' | 'nights'> {
  const first_date = body.first_date;
  const last_date = body.last_date || first_date;
  if (last_date < first_date) throw new ApiError(422, 'The last day comes before the first');
  if (first_date < isoDate(new Date())) throw new ApiError(422, 'Pick a date from today on');
  const nights = nightsOf(day, first_date, last_date);
  if (!nights.length) throw new ApiError(422, 'Those dates hold no raid night for this team');
  const note = body.note?.trim() ?? '';
  if (!note) throw new ApiError(422, 'Add a note so the officers know why');
  const clash = (r: Absence) => r.member_id === ME && r.raid_day === day && r.id !== editing && r.first_date <= last_date && first_date <= r.last_date;
  if (rows.some(clash)) throw new ApiError(409, 'You already have an absence on those dates; change that one instead');
  return { first_date, last_date, note, nights };
}

const soonest = (a: Absence, b: Absence) => a.first_date.localeCompare(b.first_date) || a.id - b.id;

export const previewAbsences: AbsencesBackend = {
  async mine() {
    return rows.filter((r) => r.member_id === ME).sort(soonest);
  },
  async report(day: string, body: AbsenceIn) {
    const checked = check(day, body);
    const row: Absence = { id: Math.max(0, ...rows.map((r) => r.id)) + 1, member_id: ME, member_name: 'Hopscotch', raid_day: day, ...checked };
    rows = [...rows, row];
    return row;
  },
  async change(day: string, id: number, body: AbsenceIn) {
    const held = rows.find((r) => r.id === id && r.member_id === ME && r.raid_day === day);
    if (!held) throw new ApiError(404, 'No such absence');
    const row: Absence = { ...held, ...check(day, body, id) };
    rows = rows.map((r) => (r.id === id ? row : r));
    return row;
  },
  async cancel(id: number) {
    if (!rows.some((r) => r.id === id && r.member_id === ME)) throw new ApiError(404, 'No such absence');
    rows = rows.filter((r) => r.id !== id);
  },
  async team(day: string): Promise<TeamAbsences> {
    const absences = rows.filter((r) => r.raid_day === day).sort(soonest);
    const nights = Array.from({ length: 8 }, (_, n) => night(day, n)).map((date) => ({
      date,
      absent: absences.filter((a) => a.first_date <= date && date <= a.last_date)
    }));
    return { raid_day: day, nights, absences };
  }
};
