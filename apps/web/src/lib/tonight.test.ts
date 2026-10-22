import { describe, expect, it } from 'vitest';
import { tonight } from './tonight';
import { linkHost, linkProblem } from './night-links';
import type { Absence } from './absences';
import type { PoolEntry } from './comp';

const absence = (member_id: number, member_name: string, note: string | null = null): Absence =>
  ({ id: member_id, member_id, member_name, raid_day: 'wed', first_date: '', last_date: '', note, nights: [] }) as Absence;
const entry = (member_id: number, name: string, primary: string | null): PoolEntry => ({
  member_id,
  name,
  wow_class: null,
  primary,
  secondary: null,
  signed_in: true
});

describe('tonight', () => {
  const pool = [entry(1, 'Hopscotch', 'shaman-elemental'), entry(2, 'Lilypadd', 'shaman-restoration'), entry(3, 'Ribbit', null)];

  it('names who is away from the next night with their spec, and what that leaves short', () => {
    const t = tonight(
      {
        raid_day: 'wed',
        nights: [
          { date: '2026-10-21', absent: [absence(2, 'Lilypadd', 'Working late.'), absence(99, 'Ribbit')] },
          { date: '2026-10-28', absent: [absence(1, 'Hopscotch')] }
        ],
        absences: []
      },
      pool
    );
    expect(t).toEqual({
      date: '2026-10-21',
      roster: 3,
      away: [
        { name: 'Lilypadd', note: 'Working late.', spec: 'Restoration Shaman', role: 'healer', onRoster: true },
        { name: 'Ribbit', note: null, spec: '', role: null, onRoster: true }
      ],
      short: [{ role: 'healer', count: 1 }],
      unknown: 1
    });
  });

  it('never says someone off the roster has no specs set', () => {
    const t = tonight({ raid_day: 'wed', nights: [{ date: '2026-10-21', absent: [absence(50, 'Bogwort')] }], absences: [] }, []);
    expect(t?.away[0]).toMatchObject({ spec: '', role: null, onRoster: false });
    expect(t).toMatchObject({ roster: 0, short: [], unknown: 1 });
  });

  it('has nothing to say with no nights ahead', () => {
    expect(tonight({ raid_day: 'wed', nights: [], absences: [] }, pool)).toBeNull();
  });
});

describe('night links', () => {
  it('asks for a name and a full https link', () => {
    expect(linkProblem('', 'https://drive.google.com/x')).toMatch(/name/);
    expect(linkProblem('Roles', 'drive.google.com/x')).toMatch(/https/);
    expect(linkProblem('Roles', 'http://drive.google.com/x')).toMatch(/https/);
    expect(linkProblem('Roles', 'javascript:alert(1)')).toMatch(/https/);
    expect(linkProblem('Roles', 'https://[abc')).toMatch(/https/);
    expect(linkProblem('Roles', 'https://example.com:abc/x')).toMatch(/https/);
    expect(linkProblem('Roles', 'https://drive.google.com/x')).toBeNull();
  });

  it('says where a link goes', () => {
    expect(linkHost('https://docs.google.com/document/d/1')).toBe('Google Drive');
    expect(linkHost('https://www.wowhead.com/tbc')).toBe('wowhead.com');
    expect(linkHost('nope')).toBe('');
  });
});
