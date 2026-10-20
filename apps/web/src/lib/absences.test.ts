import { describe, expect, it } from 'vitest';
import { dayName, monthGrid, raidDaysOf, rangeLabel, weekdayOf, type Absence } from './absences';
import { dayToad, defaultDay } from './raid-page';

const NAMES = { wed: 'Wednesday', sun: 'Sunday' };

describe('raidDaysOf', () => {
  it('shows a member only their own team', () => {
    const r = raidDaysOf({ raid_days: ['sun'], officer_days: [], day_names: NAMES });
    expect(r.days).toEqual(['sun']);
    expect(defaultDay(r)).toBe('sun');
  });
  it('shows a super admin every night in config order, opening on their own team', () => {
    const r = raidDaysOf({ raid_days: ['sun'], officer_days: ['wed', 'sun'], day_names: NAMES });
    expect(r.days).toEqual(['wed', 'sun']);
    expect(defaultDay(r)).toBe('sun');
    expect(defaultDay(raidDaysOf({ raid_days: [], officer_days: ['wed', 'sun'], day_names: NAMES }))).toBe('wed');
  });
  it('copes with no session and an older hub without day names', () => {
    expect(raidDaysOf(null).days).toEqual([]);
    expect(defaultDay(raidDaysOf(null))).toBe('');
    expect(raidDaysOf({ raid_days: ['wed'], officer_days: [] }).days).toEqual(['wed']);
    expect(dayName('wed')).toBe('Wednesday');
    expect(dayName('thu')).toBe('Thursday');
    expect(dayName('fri')).toBe('Fri');
    expect(dayName('wed', { wed: 'Midweek' })).toBe('Midweek');
  });
});

describe('calendar helpers', () => {
  it('reads the weekday from a raid day name', () => {
    expect(weekdayOf('Wednesday')).toBe(3);
    expect(weekdayOf('Sunday raid')).toBe(0);
    expect(weekdayOf('Weekend')).toBeNull();
  });
  it('lays out a month Monday first with raid nights and absences', () => {
    const away: Absence = {
      id: 1,
      member_id: 1,
      member_name: 'Hopscotch',
      raid_day: 'wed',
      first_date: '2026-10-28',
      last_date: '2026-11-04',
      note: null,
      nights: ['2026-10-28', '2026-11-04']
    };
    const weeks = monthGrid(2026, 9, '2026-10-19', [{ id: 'wed', weekday: 3 }], [away]);
    expect(weeks[0][0].date).toBe('2026-09-28');
    expect(weeks.every((w) => w.length === 7)).toBe(true);
    const days = weeks.flat();
    expect(days.filter((d) => d.inMonth && d.raids.length).map((d) => d.day)).toEqual([7, 14, 21, 28]);
    expect(days.find((d) => d.date === '2026-10-14')?.past).toBe(true);
    expect(days.find((d) => d.date === '2026-10-28')?.away).toEqual([away]);
    // The days between two raid nights of the range are not missed nights.
    expect(days.find((d) => d.date === '2026-10-30')?.away).toEqual([]);
    expect(rangeLabel(away)).toBe('Wed 28 Oct to Wed 4 Nov');
    expect(rangeLabel({ first_date: '2026-10-28', last_date: '2026-10-28' })).toBe('Wed 28 Oct');
  });
  it('gives each night its toad', () => {
    expect(dayToad('wed')).toBe('days/wednesday-toad-badge');
    expect(dayToad('sun')).toBe('days/sunday-toad-badge');
    expect(dayToad('thu')).toBe('days/thursday-toad-badge');
    // A night whose config id the web app does not know still finds its toad by name.
    expect(dayToad('t3', 'Thursday')).toBe('days/thursday-toad-badge');
    expect(dayToad('fri')).toBe('ranks/member-badge');
  });
});
