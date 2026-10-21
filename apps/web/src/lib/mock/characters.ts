/**
 * Sample character pages for the static preview, shaped as wcl_app.character_pages builds them
 * (guides/character_pages.md in lgriffin/warcraftlogs_project): Hopscotch has five raids as melee, so Me draws the
 * trend; Lilypadd has two as a healer, so Me says the history is still building (REQ-HUB-ME-004).
 */

import type { ChartPayload } from '../charts';
import type { CharacterPage, CharacterRaid, MyCharacterPage, MyRaidLine, Role, Spread } from '../characters';

const compact = (n: number) =>
  n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1_000 ? `${(n / 1_000).toFixed(1)}K` : String(n);

type Sample = [report: string, title: string, date: string, weekday: number, value: number, median: number, rank: number, of: number];

function raids(role: Role, metric: string, samples: Sample[], percent: number | null = null): CharacterRaid[] {
  return samples.map(([report_id, title, date, weekday, value, median, rank, of]) => ({
    report_id,
    title,
    zone: title,
    raid_date: `${date} 20:00:00`,
    weekday,
    role,
    metric,
    value,
    display: compact(value),
    median,
    median_display: compact(median),
    rank,
    of,
    percent
  }));
}

function chart(role: Role, metric: string, recent: CharacterRaid[]): ChartPayload {
  const shown = [...recent].reverse();
  const top = Math.max(...shown.flatMap((r) => [r.value, r.median ?? 0]));
  const name = role === 'melee' ? 'Melee' : 'Healer';
  return {
    version: 1,
    id: `character_${role}`,
    title: `${metric} as ${name.toLowerCase()}`,
    kind: 'line',
    subtitle: `Your last ${shown.length} raids as ${name.toLowerCase()}, against the raid's median`,
    x_label: 'Raid',
    y_label: metric,
    categories: shown.map((r) => `${r.raid_date.slice(8, 10)}/${r.raid_date.slice(5, 7)}`),
    series: [
      { key: 'you', name: 'You', values: shown.map((r) => r.value), display: shown.map((r) => r.display), emphasis: true },
      { key: 'median', name: `${name} median`, values: shown.map((r) => r.median), display: shown.map((r) => r.median_display), emphasis: false }
    ],
    y_max: Math.ceil(top / 2_000_000) * 2_000_000,
    references: [],
    notes: [],
    empty: ''
  };
}

const spread = (name: string, values: number[], role = ''): Spread => ({
  name,
  min: Math.min(...values),
  mean: values.reduce((a, b) => a + b, 0) / values.length,
  max: Math.max(...values),
  raids: values.length,
  total: values.reduce((a, b) => a + b, 0),
  role,
  raids_used: values.filter((v) => v > 0).length
});

function page(name: string, player_class: string, role: Role, metric: string, recent: CharacterRaid[], extra: Partial<CharacterPage>): CharacterPage {
  const best = recent.reduce((a, b) => (b.value > a.value ? b : a));
  return {
    version: 1,
    name,
    player_class,
    raids: recent.length,
    first_raid: recent.at(-1)!.raid_date,
    last_raid: recent[0].raid_date,
    role_counts: { [role]: recent.length },
    recent,
    metrics: [spread(metric, recent.map((r) => r.value), role)],
    casts: [],
    consumables: [],
    bests: [{ metric, role, value: best.value, display: best.display, report_id: best.report_id, raid_date: best.raid_date }],
    charts: [chart(role, metric, recent)],
    ...extra
  };
}

// The preview's sample raids (preview/logs-fake.ts), so each row opens a raid page the preview holds.
const hopscotchRaids = raids('melee', 'Damage', [
  ['pondWed1014', 'Serpentshrine Cavern', '2026-10-14', 2, 9_180_000, 8_060_000, 2, 3],
  ['pondSun1011', 'Tempest Keep', '2026-10-11', 6, 8_520_000, 7_640_000, 2, 8],
  ['pondWed1007', 'Serpentshrine Cavern', '2026-10-07', 2, 7_910_000, 7_710_000, 5, 9],
  ['pondSun1004', 'Serpentshrine Cavern', '2026-10-04', 6, 7_430_000, 7_100_000, 3, 8],
  ['pondWed0930', 'Tempest Keep', '2026-09-30', 2, 7_260_000, 6_970_000, 4, 8]
]);

const hopscotch = page('Hopscotch', 'Rogue', 'melee', 'Damage', hopscotchRaids, {
  metrics: [
    spread('Damage', hopscotchRaids.map((r) => r.value), 'melee'),
    spread('Total casts', [1_412, 1_380, 1_301, 702, 688]),
    spread('Consumables used', [9, 8, 7, 5, 6]),
    spread('Flask or elixir pair', [1, 1, 1, 0, 1])
  ],
  casts: [
    spread('Sinister Strike', [702, 688, 650, 351, 340], 'melee'),
    spread('Slice and Dice', [96, 90, 88, 48, 45], 'melee'),
    spread('Kick', [14, 11, 12, 4, 6], 'melee')
  ],
  consumables: [
    spread('Haste Potion', [3, 3, 2, 2, 2]),
    spread('Flask of Relentless Assault', [1, 1, 1, 0, 1]),
    spread('Drums of Battle', [4, 3, 3, 2, 2])
  ]
});

const lilypadd = page(
  'Lilypadd',
  'Shaman',
  'healer',
  'Healing',
  raids(
    'healer',
    'Healing',
    [
      ['pondThu1015', 'Tempest Keep', '2026-10-15', 3, 4_980_000, 5_050_000, 3, 6],
      ['pondSun1011', 'Tempest Keep', '2026-10-11', 6, 4_640_000, 4_510_000, 2, 6]
    ],
    18.4
  ),
  {}
);

const PAGES: Record<string, CharacterPage> = { Hopscotch: hopscotch, Lilypadd: lilypadd };

/** GET /api/me/character-page as the preview's member sees it, for `name` or their main character. */
export function previewCharacterPage(name: string | null = null): MyCharacterPage {
  return {
    generated_at: '2026-10-16 08:00:00',
    page: PAGES[name ?? ''] ?? hopscotch,
    matched_by: 'chosen',
    looked_for: ['Hopscotch', 'Lilypadd'],
    characters: Object.keys(PAGES),
    main: 'Hopscotch'
  };
}

/** GET /api/me/raid-line as the preview's member sees it: the first of their characters in the raid. */
export async function previewRaidLine(report: string): Promise<MyRaidLine | null> {
  for (const page of Object.values(PAGES)) {
    const raid = page.recent.find((r) => r.report_id === report);
    if (raid) return { name: page.name, raid };
  }
  return null;
}
