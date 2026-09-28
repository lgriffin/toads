/**
 * A sample of the analyzer's home page for the static preview, in the exact shape wcl_app.home builds
 * (guides/home_widgets.md in lgriffin/warcraftlogs_project). Raid links use the preview's raid ids so they open.
 */
import type { ChartPayload } from '../charts';
import { compact } from '../charts';
import type { AnalyzerPage, Column, PayloadWidget, Row } from '../home-payload';
import { badgeHolders } from './badges';
import { raids } from './data';

const last = raids[0];
const raidLink = (id: string) => ({ kind: 'raid' as const, params: { report_id: id } });
const blank = { subtitle: '', link: null, empty: '', error: '' };
const col = (key: string, label: string, align: 'left' | 'right' = 'left'): Column => ({ key, label, align });
const day = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });

function rows(columns: Column[], data: (string | number)[][]): Row[] {
  return data.map((r) => ({
    cells: Object.fromEntries(columns.map((c, i) => [c.key, String(r[i])])),
    values: Object.fromEntries(columns.map((c, i) => [c.key, r[i]])),
    link: null
  }));
}

function table(id: string, title: string, columns: Column[], data: (string | number)[][]): PayloadWidget {
  return { id, title, kind: 'table', size: 'half', ...blank, subtitle: `${last.zone} · ${day(last.date)}`, columns, rows: rows(columns, data) };
}

// Twelve weeks of healing per raid, as wcl_app.healing builds them: a missed week, a dip and a recovery.
const weeks = ['7 Jul', '14 Jul', '21 Jul', '28 Jul', '4 Aug', '11 Aug', '18 Aug', '25 Aug', '1 Sep', '8 Sep', '15 Sep', '22 Sep'];
const perRaid = [3.6e6, 3.7e6, 3.9e6, null, 3.8e6, 4.0e6, 3.5e6, 3.9e6, 4.1e6, 4.2e6, 4.0e6, 4.4e6];
const shown = (v: number | null) => (v === null ? '-' : compact(v));
const healingChart: ChartPayload = {
  version: 1,
  id: 'healing_weekly',
  title: 'Weekly healing',
  kind: 'bar',
  subtitle: 'Effective healing per raid, weeks from Monday, last 12 weeks',
  x_label: 'Week starting',
  y_label: 'Healing per raid',
  categories: weeks,
  series: [{ key: 'healing_per_raid', name: 'Healing per raid', values: perRaid, display: perRaid.map(shown), emphasis: true }],
  y_max: 5e6,
  references: [{ key: 'baseline', label: '4-week average', value: 4.05e6, display: '4.0M' }],
  notes: [
    'Per raid 4.4M: up, 8.6% above its 4-week average of 4.0M.',
    'Per character 1.1M: up, 7.3% above its 4-week average of 1.0M.',
    'Week of 22 Sep: +10.0% on the week before it raided.',
    'Overheal that week: 28.4%.'
  ],
  empty: ''
};
const healers: [string, (number | null)[]][] = [
  ['Lilypad', [1.1e6, 1.2e6, 1.2e6, null, 1.1e6, 1.3e6, 1.0e6, 1.2e6, 1.3e6, 1.3e6, 1.2e6, 1.4e6]],
  ['Croakwell', [0.9e6, 1.0e6, 1.0e6, null, 1.0e6, 1.0e6, 0.9e6, 1.1e6, 1.1e6, 1.2e6, 1.1e6, 1.2e6]],
  ['Mossbottom', [null, null, 0.8e6, null, 0.9e6, 0.9e6, 0.8e6, 0.9e6, 1.0e6, 1.0e6, 1.0e6, 1.1e6]],
  ['Duckweed', [0.8e6, 0.8e6, 0.9e6, null, 0.8e6, null, null, 0.7e6, 0.8e6, 0.9e6, 0.9e6, 0.9e6]]
];
// Healing per healer per raid across all four healers, week by week.
const perCharacter = weeks.map((_, i) => {
  const v = healers.map(([, values]) => values[i]).filter((x): x is number => x !== null);
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
});
const healersChart: ChartPayload = {
  ...healingChart,
  id: 'healers_weekly',
  title: 'Healers week on week',
  kind: 'line',
  subtitle: "Healing per raid attended as a healer, against the guild's average per character",
  series: [
    { key: 'average', name: 'Average per character', values: perCharacter, display: perCharacter.map(shown), emphasis: true },
    ...healers.map(([name, values]) => ({ key: name.toLowerCase(), name, values, display: values.map(shown), emphasis: false }))
  ],
  y_max: 1.5e6,
  references: [],
  notes: []
};

const kills = last.bosses.filter((b) => b.killed);
const dmgCols = [col('rank', '#', 'right'), col('name', 'Name'), col('class', 'Class'), col('damage', 'Damage', 'right'), col('share', 'Share', 'right')];
const healCols = [col('rank', '#', 'right'), col('name', 'Name'), col('class', 'Class'), col('healing', 'Healing', 'right'), col('overheal', 'Overheal', 'right')];

export const analyzerPage: AnalyzerPage = {
  version: 1,
  generated_at: '2026-09-26 18:00:00',
  widgets: [
    {
      id: 'guild_snapshot',
      title: 'Guild at a glance',
      kind: 'stats',
      size: 'full',
      ...blank,
      tiles: [
        { label: 'Raids stored', value: 42, display: '42', hint: 'Guild raids, reference reports left out' },
        { label: 'Active raiders', value: 31, display: '31', hint: 'In any of the last 10 raids' },
        { label: 'Raids in 30 days', value: 9, display: '9', hint: '' },
        { label: 'Last raid', value: last.date, display: day(last.date), hint: '' },
        { label: 'Days since', value: 2, display: '2', hint: '' }
      ]
    },
    {
      id: 'last_raid',
      title: 'Last raid',
      kind: 'stats',
      size: 'full',
      ...blank,
      subtitle: `${last.zone} · ${last.raidDay}`,
      link: raidLink(last.id),
      tiles: [
        { label: 'Date', value: last.date, display: day(last.date), hint: '' },
        { label: 'Duration', value: last.durationMin * 60, display: `${Math.floor(last.durationMin / 60)}h ${last.durationMin % 60}m`, hint: '' },
        { label: 'Bosses killed', value: kills.length, display: `${kills.length}/${last.bosses.length}`, hint: '' },
        { label: 'Raid size', value: last.size, display: String(last.size), hint: '' },
        { label: 'Total damage', value: 48_600_000, display: '48.6M', hint: '' },
        { label: 'Total healing', value: 21_300_000, display: '21.3M', hint: '' }
      ]
    },
    {
      id: 'recent_raids',
      title: 'Recent raids',
      kind: 'list',
      size: 'half',
      ...blank,
      items: raids.map((r) => ({
        label: r.zone,
        detail: `${day(r.date)} · ${r.raidDay} · ${r.bosses.filter((b) => b.killed).length}/${r.bosses.length} bosses`,
        link: raidLink(r.id)
      }))
    },
    {
      id: 'raid_activity',
      title: 'Raid activity',
      kind: 'bars',
      size: 'half',
      ...blank,
      subtitle: 'Raids per week',
      bars: [
        ['3 Aug', 2],
        ['10 Aug', 3],
        ['17 Aug', 2],
        ['24 Aug', 2],
        ['31 Aug', 3],
        ['7 Sep', 3],
        ['14 Sep', 4],
        ['21 Sep', 3]
      ].map(([label, n]) => ({ label: `Week of ${label}`, value: Number(n), display: String(n) }))
    },
    { id: 'healing_weekly', title: 'Weekly healing', kind: 'chart', size: 'full', ...blank, subtitle: healingChart.subtitle, chart: healingChart },
    { id: 'healers_weekly', title: 'Healers week on week', kind: 'chart', size: 'full', ...blank, subtitle: healersChart.subtitle, chart: healersChart },
    table('top_damage', 'Top damage', dmgCols, [
      [1, 'Hopscotch', 'Rogue', '2.61M', '5.4%'],
      [2, 'Bogwalker', 'Warrior', '2.48M', '5.1%'],
      [3, 'Wartsworth', 'Mage', '2.40M', '4.9%'],
      [4, 'Greenmantle', 'Warlock', '2.33M', '4.8%'],
      [5, 'Tadpole', 'Hunter', '2.19M', '4.5%']
    ]),
    table('top_healing', 'Top healing', healCols, [
      [1, 'Lilypadd', 'Shaman', '3.02M', '18.2%'],
      [2, 'Mossback', 'Priest', '2.87M', '24.9%'],
      [3, 'Reedsong', 'Druid', '2.51M', '31.0%'],
      [4, 'Puddlelight', 'Paladin', '2.30M', '12.7%'],
      [5, 'Croakwell', 'Priest', '1.96M', '22.4%']
    ]),
    {
      ...table('attendance', 'Attendance', [col('name', 'Name'), col('class', 'Class'), col('raids', 'Raids', 'right'), col('attendance', 'Attendance', 'right')], [
        ['Hopscotch', 'Rogue', 10, '100.0%'],
        ['Lilypadd', 'Shaman', 10, '100.0%'],
        ['Bogwalker', 'Warrior', 9, '90.0%'],
        ['Mossback', 'Priest', 9, '90.0%'],
        ['Wartsworth', 'Mage', 8, '80.0%']
      ]),
      subtitle: 'Last 10 raids'
    },
    {
      id: 'badges',
      title: 'Toads badges',
      kind: 'badges',
      size: 'half',
      ...blank,
      subtitle: `${last.zone} · ${day(last.date)}`,
      holders: badgeHolders
    },
    table(
      'boss_kills',
      'Boss kills',
      [col('boss', 'Boss'), col('time', 'Kill time', 'right'), col('players', 'Players', 'right')],
      kills.map((b) => [b.name, `${Math.floor(b.seconds / 60)}:${String(b.seconds % 60).padStart(2, '0')}`, last.size])
    ),
    {
      id: 'class_mix',
      title: 'Class mix',
      kind: 'bars',
      size: 'half',
      ...blank,
      subtitle: last.zone,
      bars: [
        ['Priest', 4],
        ['Warrior', 4],
        ['Shaman', 3],
        ['Mage', 3],
        ['Warlock', 3],
        ['Rogue', 2],
        ['Hunter', 2],
        ['Druid', 2],
        ['Paladin', 2]
      ].map(([label, n]) => ({ label: String(label), value: Number(n), display: String(n) }))
    },
    table(
      'interrupts',
      'Interrupt casts',
      [col('name', 'Name'), col('count', 'Casts', 'right')],
      last.interrupts.map((i) => [i.player, i.count])
    ),
    table('consumables', 'Consumables', [col('name', 'Name'), col('role', 'Role'), col('used', 'Used', 'right')], [
      ['Bogwalker', 'Tank', 14],
      ['Hopscotch', 'Melee', 12],
      ['Wartsworth', 'Ranged', 11],
      ['Lilypadd', 'Healer', 9],
      ['Tadpole', 'Ranged', 8]
    ])
  ]
};
