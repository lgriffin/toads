import { describe, expect, it } from 'vitest';
import {
  bossHistory,
  defaultNight,
  getNightPage,
  getNights,
  logNights,
  filterRaids,
  getRaid,
  raidDateLabel,
  raidLength,
  raidsPerWeekday,
  sumBoss,
  tabsFor,
  toggleWeekday,
  weekdayName,
  type BossHistory,
  type RaidPage,
  type RaidRow
} from './logs';
import { PREVIEW_RAID_IDS, previewLogs, previewViewer } from './preview/logs-fake';

function row(report_id: string, weekday: number | null, zone = 'Serpentshrine Cavern'): RaidRow {
  return {
    summary: { report_id, title: `Raid ${report_id}`, zone, raid_date: '2026-10-14 19:30:00', weekday, size: 25, url: '' },
    analysed: true,
    day: null,
    full: false
  };
}

const ROWS = [row('wed', 2), row('thu', 3, 'Tempest Keep'), row('sun', 6), row('undated', null)];

describe('the raid list', () => {
  it('shows every raid until a weekday is picked, then only those days', () => {
    expect(filterRaids(ROWS, { weekdays: [], zone: '', query: '' })).toHaveLength(4);
    expect(filterRaids(ROWS, { weekdays: [2, 3], zone: '', query: '' }).map((r) => r.summary.report_id)).toEqual([
      'wed',
      'thu'
    ]);
  });
  it('narrows by zone and by title or zone text', () => {
    expect(filterRaids(ROWS, { weekdays: [], zone: 'Tempest Keep', query: '' }).map((r) => r.summary.report_id)).toEqual(['thu']);
    expect(filterRaids(ROWS, { weekdays: [], zone: '', query: ' tempest ' })).toHaveLength(1);
    expect(filterRaids(ROWS, { weekdays: [], zone: '', query: 'raid sun' })).toHaveLength(1);
  });
  it('counts raids per weekday and toggles the chips', () => {
    expect(raidsPerWeekday(ROWS)).toEqual([0, 0, 1, 1, 0, 0, 1]);
    expect(toggleWeekday([6], 2)).toEqual([2, 6]);
    expect(toggleWeekday([2, 6], 6)).toEqual([2]);
  });
  it('labels days and lengths', () => {
    expect(weekdayName(2)).toBe('Wednesday');
    expect(weekdayName(null)).toBe('Unknown day');
    expect(raidLength(7_500_000)).toBe('2h 05m');
    expect(raidLength(2_520_000)).toBe('42m');
    expect(raidLength(0)).toBe('—');
    expect(raidDateLabel(ROWS[0].summary)).toBe('Wed, 14 Oct 2026');
    expect(raidDateLabel({ ...ROWS[0].summary, raid_date: '' })).toBe('—');
  });
});

const HYDROSS: BossHistory = {
  encounter_id: 623,
  name: 'Hydross',
  days: {
    '2': {
      kills: 2,
      duration_ms: 600_000,
      damage: 6_000_000,
      healing: 3_000_000,
      players: [{ name: 'Hopscotch', player_class: 'Rogue', role: 'melee', kills: 2, damage: 2_000_000, healing: 0, damage_taken: 1 }]
    },
    '3': { kills: 1, duration_ms: 300_000, damage: 3_000_000, healing: 0 }
  }
};

describe('the boss history', () => {
  it('adds up the picked weekdays and averages per kill', () => {
    const all = sumBoss(HYDROSS, [])!;
    expect(all.kills).toBe(3);
    expect(all.duration_ms).toBe(300_000);
    expect(all.dps).toBe(10_000);
    expect(all.partial).toBe(true);
    expect(all.players![0].damage_per_kill).toBe(1_000_000);
  });
  it('shows per-raider numbers only for days that carry them', () => {
    expect(sumBoss(HYDROSS, [3])!.players).toBeNull();
    expect(sumBoss(HYDROSS, [2])!.partial).toBe(false);
    expect(sumBoss(HYDROSS, [6])).toBeNull();
    expect(bossHistory([HYDROSS, { encounter_id: 1, name: 'Other', days: {} }], [])).toHaveLength(1);
  });
});

describe('the raid view', () => {
  it('offers only the tabs a raid has anything on', async () => {
    const view = await previewLogs(() => 'admin').raid(PREVIEW_RAID_IDS[0], null);
    expect(view.full).toBe(true);
    const page = view.page as RaidPage;
    expect(tabsFor(page)).toContain('healers');
    expect(tabsFor({ ...page, engineering: [], composition: { tanks: [], healers: [], melee: [], ranged: [] } })).not.toContain(
      'engineering'
    );
    expect(tabsFor({ ...page, composition: { tanks: [], healers: [], melee: [], ranged: [] } })).not.toContain('composition');
  });
  it('reads under the raid day when the list gives one', async () => {
    const seen: string[] = [];
    const f = (async (url: string) => {
      seen.push(url);
      return new Response(JSON.stringify({ full: false, page: {} }), { status: 200 });
    }) as unknown as typeof fetch;
    await getRaid('abc', 'wed', f);
    await getRaid('abc', null, f);
    expect(seen).toEqual(['/api/days/wed/logs/abc', '/api/logs/abc']);
  });
});

describe('the preview', () => {
  it('follows the API: members see overviews, the Wednesday officer Wednesdays, super admins everything', async () => {
    const member = await previewLogs(() => 'member').overview();
    expect(member.raids.every((r) => !r.full)).toBe(true);
    expect(member.bosses.every((b) => Object.values(b.days).every((d) => d.players === undefined))).toBe(true);
    const officer = await previewLogs(() => 'officer').overview();
    expect(officer.raids.filter((r) => r.full).every((r) => r.summary.weekday === 2 && r.day === 'wed')).toBe(true);
    expect(officer.full_weekdays).toEqual([2]);
    const admin = await previewLogs(() => 'admin').overview();
    expect(admin.raids.every((r) => r.full && r.day === null)).toBe(true);
    const thursday = admin.raids.find((r) => r.summary.weekday === 3)!;
    const shown = await previewLogs(() => 'officer').raid(thursday.summary.report_id, null);
    expect(shown.full).toBe(false);
    expect(JSON.stringify(shown.page)).not.toContain('Hopscotch');
    await expect(previewLogs(() => 'admin').raid('missing', null)).rejects.toThrow();
  });
});

describe('the night Logs opens on', () => {
  const nights = logNights({ wed: 2, thu: 3, sun: 6 }, { wed: 'Wednesday', thu: 'Thursday', sun: 'Sunday', alt: 'Alts' });
  const member = (raid_days: string[]) => ({ raid_days, global_officer: false, super_admin: false });

  it('lists only the nights the API builds, with the weekday it resolved', () => {
    expect(nights).toEqual([
      { id: 'wed', name: 'Wednesday', weekday: 2 },
      { id: 'thu', name: 'Thursday', weekday: 3 },
      { id: 'sun', name: 'Sunday', weekday: 6 }
    ]);
    // A raid_sheets.yaml weekday wins over the name, and an unknown id keeps its id as its name.
    expect(logNights({ fri: 4, wed: 5 }, undefined)).toEqual([
      { id: 'fri', name: 'fri', weekday: 4 },
      { id: 'wed', name: 'Wednesday', weekday: 5 }
    ]);
  });

  it("opens on the night of the viewer's Toad badge", () => {
    expect(defaultNight(member(['wed']), nights)).toBe('wed');
    expect(defaultNight(member(['sun']), nights)).toBe('sun');
    expect(defaultNight(member(['thu', 'alt']), nights)).toBe('thu');
  });

  it('opens on every raid for no night, several nights, global officers and super admins', () => {
    expect(defaultNight(member([]), nights)).toBeNull();
    // A night with no page of its own (its weekday unknown) opens on every raid.
    expect(defaultNight(member(['alt']), nights)).toBeNull();
    expect(defaultNight(member(['wed', 'sun']), nights)).toBeNull();
    expect(defaultNight({ ...member(['wed']), global_officer: true }, nights)).toBeNull();
    expect(defaultNight({ ...member(['wed']), super_admin: true }, nights)).toBeNull();
  });

  it("reads a night's widgets from the hub", async () => {
    const seen: string[] = [];
    const f = (async (url: string) => {
      seen.push(url);
      return new Response(JSON.stringify({ version: 1, generated_at: null, widgets: [] }), { status: 200 });
    }) as unknown as typeof fetch;
    await getNightPage('wed', f);
    expect(seen).toEqual(['/api/home/nights/wed']);
    const g = (async () => new Response(JSON.stringify({ nights: { wed: 2 } }), { status: 200 })) as unknown as typeof fetch;
    expect(await getNights(g)).toEqual({ wed: 2 });
  });

  it('in the preview, opens the member and officer on Wednesday and the super admin on every raid', async () => {
    expect(defaultNight(previewViewer('member'), nights)).toBe('wed');
    expect(defaultNight(previewViewer('officer'), nights)).toBe('wed');
    expect(defaultNight(previewViewer('admin'), nights)).toBeNull();
    const ids = async (role: 'member' | 'officer') => (await previewLogs(() => role).widgets('wed')).widgets.map((w) => w.id);
    expect(await ids('member')).not.toContain('badges');
    expect(await ids('officer')).toContain('badges');
  });
});
