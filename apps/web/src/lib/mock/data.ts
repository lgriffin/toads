/**
 * Sample data for the static preview (PREVIEW=1 builds published to GitHub Pages).
 * Shapes are what the pages need, not the API contract; swap each page's load for an API call when it lands.
 */

export const MOCK_NOW = new Date('2026-09-26T18:00:00Z');

export type Role = 'Tank' | 'Healer' | 'Melee' | 'Ranged';
export type RaidDay = 'Wednesday' | 'Sunday';

export interface NextRaid {
  zone: string;
  raidDay: RaidDay;
  start: string;
  signups: Record<Role, number>;
  needed: Record<Role, number>;
}

export interface BossKill {
  name: string;
  killed: boolean;
  wipes: number;
  seconds: number;
}

export interface ConsumeCoverage {
  name: string;
  boss: number;
  trash: number;
}

export interface Raid {
  id: string;
  code: string;
  zone: string;
  raidDay: RaidDay;
  size: 10 | 25;
  date: string;
  durationMin: number;
  deaths: number;
  roles: Record<Role, number>;
  bosses: BossKill[];
  consumes: ConsumeCoverage[];
  interrupts: { player: string; count: number }[];
  cancelledCasts: { player: string; count: number }[];
}

export interface BankSource {
  id: string;
  raidDay: RaidDay;
  bankGuild: string;
  character: string;
  snapshot: string;
  uploader: string;
}

export interface BankItem {
  source: string;
  name: string;
  count: number;
  tab: string;
  quality: 'common' | 'uncommon' | 'rare' | 'epic';
}

export interface MeRaid {
  raidId: string;
  date: string;
  zone: string;
  mine: number;
  median: number;
}

export interface Receipt {
  item: string;
  count: number;
  date: string;
  request: string;
}

export const nextRaid: NextRaid = {
  zone: 'Serpentshrine Cavern',
  raidDay: 'Sunday',
  start: '2026-09-27T18:30:00Z',
  signups: { Tank: 3, Healer: 6, Melee: 7, Ranged: 8 },
  needed: { Tank: 3, Healer: 7, Melee: 7, Ranged: 8 }
};

const TBC_CONSUMES = ['Flask or elixirs', 'Food buff', 'Weapon oil or stone', 'Potion used'];

function coverage(seed: number): ConsumeCoverage[] {
  return TBC_CONSUMES.map((name, i) => ({
    name,
    boss: Math.min(100, 70 + ((seed * 7 + i * 11) % 30)),
    trash: Math.min(100, 30 + ((seed * 13 + i * 17) % 45))
  }));
}

const RAIDS: Raid[] = [
  {
    id: 'ssc-0924',
    code: 'aB3xKq9Lm2',
    zone: 'Serpentshrine Cavern',
    raidDay: 'Wednesday',
    size: 25,
    date: '2026-09-24T18:30:00Z',
    durationMin: 196,
    deaths: 31,
    roles: { Tank: 3, Healer: 7, Melee: 7, Ranged: 8 },
    bosses: [
      { name: 'Hydross the Unstable', killed: true, wipes: 0, seconds: 312 },
      { name: 'The Lurker Below', killed: true, wipes: 1, seconds: 268 },
      { name: 'Leotheras the Blind', killed: true, wipes: 2, seconds: 401 },
      { name: 'Fathom-Lord Karathress', killed: true, wipes: 0, seconds: 287 },
      { name: 'Morogrim Tidewalker', killed: true, wipes: 0, seconds: 244 },
      { name: 'Lady Vashj', killed: false, wipes: 4, seconds: 0 }
    ],
    consumes: coverage(1),
    interrupts: [
      { player: 'Hopscotch', count: 14 },
      { player: 'Bogwalker', count: 11 },
      { player: 'Lilypadd', count: 6 }
    ],
    cancelledCasts: [
      { player: 'Tadpole', count: 23 },
      { player: 'Greenmantle', count: 17 },
      { player: 'Wartsworth', count: 9 }
    ]
  },
  {
    id: 'tk-0920',
    code: 'Zt7pQw1Rn8',
    zone: 'Tempest Keep',
    raidDay: 'Sunday',
    size: 25,
    date: '2026-09-20T18:30:00Z',
    durationMin: 148,
    deaths: 22,
    roles: { Tank: 3, Healer: 6, Melee: 8, Ranged: 8 },
    bosses: [
      { name: "Al'ar", killed: true, wipes: 1, seconds: 356 },
      { name: 'Void Reaver', killed: true, wipes: 0, seconds: 221 },
      { name: 'High Astromancer Solarian', killed: true, wipes: 0, seconds: 263 },
      { name: "Kael'thas Sunstrider", killed: false, wipes: 3, seconds: 0 }
    ],
    consumes: coverage(2),
    interrupts: [
      { player: 'Bogwalker', count: 19 },
      { player: 'Hopscotch', count: 12 },
      { player: 'Fenwick', count: 8 }
    ],
    cancelledCasts: [
      { player: 'Greenmantle', count: 12 },
      { player: 'Tadpole', count: 11 },
      { player: 'Reedbeard', count: 4 }
    ]
  },
  {
    id: 'kara-0913',
    code: 'Mm4vHs6Yc0',
    zone: 'Karazhan',
    raidDay: 'Sunday',
    size: 10,
    date: '2026-09-13T16:00:00Z',
    durationMin: 104,
    deaths: 6,
    roles: { Tank: 2, Healer: 3, Melee: 2, Ranged: 3 },
    bosses: [
      { name: 'Attumen the Huntsman', killed: true, wipes: 0, seconds: 118 },
      { name: 'Moroes', killed: true, wipes: 0, seconds: 164 },
      { name: 'Maiden of Virtue', killed: true, wipes: 0, seconds: 131 },
      { name: 'Opera Event', killed: true, wipes: 0, seconds: 142 },
      { name: 'The Curator', killed: true, wipes: 0, seconds: 176 },
      { name: 'Shade of Aran', killed: true, wipes: 1, seconds: 203 },
      { name: 'Netherspite', killed: true, wipes: 0, seconds: 229 },
      { name: 'Prince Malchezaar', killed: true, wipes: 0, seconds: 247 }
    ],
    consumes: coverage(3),
    interrupts: [
      { player: 'Fenwick', count: 9 },
      { player: 'Lilypadd', count: 5 }
    ],
    cancelledCasts: [{ player: 'Reedbeard', count: 7 }]
  },
  {
    id: 'ssc-0917',
    code: 'Qe2kLt5Wz3',
    zone: 'Serpentshrine Cavern',
    raidDay: 'Wednesday',
    size: 25,
    date: '2026-09-17T18:30:00Z',
    durationMin: 211,
    deaths: 38,
    roles: { Tank: 3, Healer: 7, Melee: 6, Ranged: 9 },
    bosses: [
      { name: 'Hydross the Unstable', killed: true, wipes: 1, seconds: 330 },
      { name: 'The Lurker Below', killed: true, wipes: 0, seconds: 281 },
      { name: 'Leotheras the Blind', killed: true, wipes: 3, seconds: 422 },
      { name: 'Fathom-Lord Karathress', killed: true, wipes: 1, seconds: 301 },
      { name: 'Morogrim Tidewalker', killed: true, wipes: 0, seconds: 259 },
      { name: 'Lady Vashj', killed: false, wipes: 2, seconds: 0 }
    ],
    consumes: coverage(4),
    interrupts: [
      { player: 'Hopscotch', count: 16 },
      { player: 'Bogwalker', count: 10 }
    ],
    cancelledCasts: [
      { player: 'Tadpole', count: 19 },
      { player: 'Wartsworth', count: 13 }
    ]
  },
  {
    id: 'gruul-0913',
    code: 'Hn8cRb1Px7',
    zone: "Gruul's Lair",
    raidDay: 'Sunday',
    size: 25,
    date: '2026-09-13T19:30:00Z',
    durationMin: 52,
    deaths: 4,
    roles: { Tank: 4, Healer: 6, Melee: 7, Ranged: 8 },
    bosses: [
      { name: 'High King Maulgar', killed: true, wipes: 0, seconds: 214 },
      { name: 'Gruul the Dragonkiller', killed: true, wipes: 0, seconds: 287 }
    ],
    consumes: coverage(5),
    interrupts: [{ player: 'Bogwalker', count: 21 }],
    cancelledCasts: [{ player: 'Greenmantle', count: 6 }]
  },
  {
    id: 'mag-0910',
    code: 'Wd6fTy3Ga9',
    zone: "Magtheridon's Lair",
    raidDay: 'Wednesday',
    size: 25,
    date: '2026-09-10T20:00:00Z',
    durationMin: 24,
    deaths: 2,
    roles: { Tank: 4, Healer: 7, Melee: 6, Ranged: 8 },
    bosses: [{ name: 'Magtheridon', killed: true, wipes: 0, seconds: 198 }],
    consumes: coverage(6),
    interrupts: [{ player: 'Hopscotch', count: 7 }],
    cancelledCasts: [{ player: 'Tadpole', count: 5 }]
  }
];

/** Newest first, as the API will return them. */
export const raids: Raid[] = [...RAIDS].sort((a, b) => b.date.localeCompare(a.date));

export const bankSources: BankSource[] = [
  {
    id: 'wed-main',
    raidDay: 'Wednesday',
    bankGuild: 'Toads Bank',
    character: 'Toadstash',
    snapshot: '2026-09-24T22:05:00Z',
    uploader: 'Croakley'
  },
  {
    id: 'sun-main',
    raidDay: 'Sunday',
    bankGuild: 'Toads Bank II',
    character: 'Pondkeeper',
    snapshot: '2026-09-15T21:40:00Z',
    uploader: 'Ribbitz'
  }
];

export const bankItems: BankItem[] = [
  { source: 'wed-main', name: 'Super Mana Potion', count: 60, tab: 'Consumables', quality: 'common' },
  { source: 'wed-main', name: 'Elixir of Major Agility', count: 40, tab: 'Consumables', quality: 'common' },
  { source: 'wed-main', name: 'Flask of Relentless Assault', count: 12, tab: 'Consumables', quality: 'common' },
  { source: 'wed-main', name: 'Primal Might', count: 3, tab: 'Mats', quality: 'rare' },
  { source: 'wed-main', name: 'Nether Vortex', count: 5, tab: 'Mats', quality: 'epic' },
  { source: 'wed-main', name: 'Pattern: Belt of Deep Shadow', count: 1, tab: 'Recipes', quality: 'epic' },
  { source: 'sun-main', name: 'Super Healing Potion', count: 45, tab: 'Consumables', quality: 'common' },
  { source: 'sun-main', name: 'Flask of Mighty Restoration', count: 8, tab: 'Consumables', quality: 'common' },
  { source: 'sun-main', name: 'Fire Protection Potion', count: 20, tab: 'Consumables', quality: 'common' },
  { source: 'sun-main', name: 'Primal Nether', count: 4, tab: 'Mats', quality: 'rare' },
  { source: 'sun-main', name: 'Enchant Weapon - Mongoose', count: 1, tab: 'Recipes', quality: 'epic' }
];

export const me = {
  name: 'Hopscotch',
  characters: [
    { name: 'Hopscotch', spec: 'Combat Rogue', role: 'Melee' as Role, metric: 'DPS' },
    { name: 'Lilypadd', spec: 'Restoration Shaman', role: 'Healer' as Role, metric: 'HPS' }
  ],
  history: {
    Hopscotch: [
      { raidId: 'mag-0910', date: '2026-09-10', zone: 'Magtheridon', mine: 1184, median: 1102 },
      { raidId: 'gruul-0913', date: '2026-09-13', zone: 'Gruul', mine: 1231, median: 1140 },
      { raidId: 'ssc-0917', date: '2026-09-17', zone: 'SSC', mine: 1098, median: 1071 },
      { raidId: 'tk-0920', date: '2026-09-20', zone: 'TK', mine: 1302, median: 1166 },
      { raidId: 'ssc-0924', date: '2026-09-24', zone: 'SSC', mine: 1275, median: 1119 }
    ],
    Lilypadd: [
      { raidId: 'kara-0913', date: '2026-09-13', zone: 'Karazhan', mine: 712, median: 655 },
      { raidId: 'tk-0920', date: '2026-09-20', zone: 'TK', mine: 690, median: 701 }
    ]
  } as Record<string, MeRaid[]>,
  receipts: [
    { item: 'Flask of Relentless Assault', count: 4, date: '2026-09-23', request: 'Wed SSC progression' },
    { item: 'Elixir of Major Agility', count: 10, date: '2026-09-16', request: 'Weekly consumables' },
    { item: 'Primal Might', count: 1, date: '2026-09-02', request: 'Dragonstrike crafting' }
  ] as Receipt[]
};

/** Claims as GET /api/claims returns them, for the claim flow page in the preview. */
export const claims: import('$lib/api').Claim[] = [
  { id: 1, member_id: 7, character_id: 101, character_name: 'Hopscotch', raid_day_id: 'wed', status: 'approved', reason: null },
  { id: 2, member_id: 7, character_id: 102, character_name: 'Lilypadd', raid_day_id: 'wed', status: 'pending', reason: null }
];

// --- reference comparison (officers) --------------------------------------------------------------

type RefMetric = import('$lib/reference').Metric;

const pct = (ours: number | null, theirs: number | null): number | null =>
  ours === null || theirs === null || theirs === 0 ? null : Math.round(((ours - theirs) / theirs) * 1000) / 10;

function refMetric(
  key: string,
  label: string,
  guild: number,
  reference: number,
  displays: [string, string],
  higher: boolean | null
): RefMetric {
  const delta = pct(guild, reference);
  // null `higher` marks a metric with no better side (raid totals, composition).
  const better = higher === null || !delta ? null : delta > 0 === higher;
  return {
    key,
    label,
    guild,
    reference,
    guild_display: displays[0],
    reference_display: displays[1],
    delta_percent: delta,
    higher_is_better: higher ?? true,
    better
  };
}

function classRow(
  player_class: string,
  role: string,
  metric: string,
  guild_count: number,
  guild_average: number | null,
  reference_count: number,
  reference_average: number | null
): import('$lib/reference').ClassRow {
  return {
    player_class,
    role,
    metric,
    guild_count,
    guild_average,
    reference_count,
    reference_average,
    delta_percent: pct(guild_average, reference_average)
  };
}

/** The preview's Wednesday officer console: two of our raids, two references and one built comparison. */
export const referenceOverview: import('$lib/reference').ReferenceOverview = {
  login: {
    configured: true,
    connected: true,
    status: 'working',
    connected_by: 'Hopscotch',
    connected_at: '2026-09-18T19:02:00Z'
  },
  generated_at: '2026-09-26T17:40:00Z',
  references: [
    {
      report_id: 'Rf5GkT2pWm8hQz3C',
      title: "Gruul's Lair",
      raid_date: '2026-09-21 20:00:00',
      zone: "Gruul's Lair",
      raid_size: 25,
      label: 'EU speed clear',
      owner: 'Nightfall Vanguard'
    },
    {
      report_id: 'Mg7LsV4bYc1nXe9D',
      title: 'Magtheridon',
      raid_date: '2026-09-19 21:15:00',
      zone: "Magtheridon's Lair",
      raid_size: 25,
      label: null,
      owner: 'Nightfall Vanguard'
    }
  ],
  guild_raids: [
    {
      report_id: 'Tq8mZr2VbX4kLp7N',
      title: 'Gruul + Magtheridon',
      raid_date: '2026-09-23 19:30:00',
      zone: "Gruul's Lair",
      raid_size: 25,
      label: null,
      owner: 'Toads'
    },
    {
      report_id: 'Hc3YwP9sNd6fJa1R',
      title: 'Gruul + Magtheridon',
      raid_date: '2026-09-16 19:30:00',
      zone: "Gruul's Lair",
      raid_size: 25,
      label: null,
      owner: 'Toads'
    }
  ],
  comparisons: [
    {
      guild_report: 'Tq8mZr2VbX4kLp7N',
      reference_report: 'Rf5GkT2pWm8hQz3C',
      guild_title: 'Gruul + Magtheridon',
      reference_title: "Gruul's Lair",
      generated_at: '2026-09-24T08:12:00Z'
    }
  ],
  jobs: [
    {
      id: 'job-4',
      kind: 'import',
      status: 'failed',
      message: 'Warcraft Logs says that report is private or does not exist.',
      report: 'Xx0Xx0Xx0Xx0Xx0X',
      created_at: '2026-09-25T20:41:00Z',
      updated_at: '2026-09-25T20:41:09Z'
    },
    {
      id: 'job-3',
      kind: 'compare',
      status: 'done',
      message: "Compared Gruul + Magtheridon with Gruul's Lair.",
      report: 'Tq8mZr2VbX4kLp7N',
      created_at: '2026-09-24T08:11:40Z',
      updated_at: '2026-09-24T08:12:00Z'
    },
    {
      id: 'job-2',
      kind: 'import',
      status: 'done',
      message: "Imported Gruul's Lair (Nightfall Vanguard).",
      report: 'Rf5GkT2pWm8hQz3C',
      created_at: '2026-09-22T09:30:00Z',
      updated_at: '2026-09-22T09:31:12Z'
    }
  ]
};

/** Our Gruul + Magtheridon night against a faster guild's Gruul-only log, so the scope note shows. */
export const referenceComparison: import('$lib/reference').ComparisonResponse = {
  generated_at: '2026-09-24T08:12:00Z',
  comparison: {
    version: 1,
    guild: {
      report_id: 'Tq8mZr2VbX4kLp7N',
      title: 'Gruul + Magtheridon',
      raid_date: '2026-09-23 19:30:00',
      zone: "Gruul's Lair",
      raid_size: 25,
      duration_ms: 3_134_000
    },
    reference: {
      report_id: 'Rf5GkT2pWm8hQz3C',
      title: "Gruul's Lair",
      raid_date: '2026-09-21 20:00:00',
      zone: "Gruul's Lair",
      raid_size: 25,
      duration_ms: 1_872_000
    },
    scope: { scoped: true, shared_encounters: 2, guild_extra_encounters: ['Magtheridon'] },
    overview: [
      refMetric('duration', 'Duration', 3134, 1872, ['52:14', '31:12'], false),
      refMetric('total_damage', 'Total damage', 14_820_000, 9_910_000, ['14.8M', '9.9M'], null),
      refMetric('total_healing', 'Total healing', 6_120_000, 3_740_000, ['6.1M', '3.7M'], null),
      refMetric('damage_taken', 'Damage taken', 7_410_000, 4_580_000, ['7.4M', '4.6M'], false),
      refMetric('damage_per_dps', 'Damage per DPS', 823_400, 586_700, ['823.4k', '586.7k'], true),
      refMetric('healing_per_healer', 'Healing per healer', 871_200, 622_900, ['871.2k', '622.9k'], true),
      refMetric('overheal', 'Overheal', 31.4, 24.8, ['31.4%', '24.8%'], false)
    ],
    composition: [
      refMetric('raid_size', 'Raid size', 25, 25, ['25', '25'], null),
      refMetric('tanks', 'Tanks', 3, 3, ['3', '3'], null),
      refMetric('healers', 'Healers', 7, 6, ['7', '6'], null),
      refMetric('melee', 'Melee', 7, 8, ['7', '8'], null),
      refMetric('ranged', 'Ranged', 8, 8, ['8', '8'], null)
    ],
    classes: [
      classRow('Warrior', 'tank', 'DPS', 3, 612, 3, 655),
      classRow('Rogue', 'melee', 'DPS', 3, 1184, 3, 1352),
      classRow('Warrior', 'melee', 'DPS', 2, 1098, 3, 1290),
      classRow('Shaman', 'melee', 'DPS', 1, 1030, 0, null),
      classRow('Hunter', 'ranged', 'DPS', 3, 1142, 2, 1203),
      classRow('Mage', 'ranged', 'DPS', 2, 1210, 3, 1302),
      classRow('Warlock', 'ranged', 'DPS', 2, 1265, 2, 1381),
      classRow('Shaman', 'healer', 'HPS', 3, 702, 2, 745),
      classRow('Priest', 'healer', 'HPS', 2, 688, 2, 731),
      classRow('Druid', 'healer', 'HPS', 1, 655, 1, 690),
      classRow('Paladin', 'healer', 'HPS', 1, 742, 1, 801)
    ],
    consumables: [
      { name: 'Flask of Relentless Assault', guild_uses: 6, guild_users: 6, reference_uses: 9, reference_users: 9 },
      { name: 'Super Mana Potion', guild_uses: 14, guild_users: 9, reference_uses: 21, reference_users: 12 },
      { name: 'Haste Potion', guild_uses: 8, guild_users: 6, reference_uses: 22, reference_users: 15 },
      { name: 'Destruction Potion', guild_uses: 4, guild_users: 3, reference_uses: 12, reference_users: 8 },
      { name: 'Dark Rune', guild_uses: 5, guild_users: 4, reference_uses: 11, reference_users: 7 },
      { name: 'Drums of Battle', guild_uses: 9, guild_users: 3, reference_uses: 18, reference_users: 5 }
    ],
    encounters: [
      {
        name: 'High King Maulgar',
        guild_duration_ms: 214_000,
        reference_duration_ms: 168_000,
        guild_damage: 3_960_000,
        reference_damage: 3_880_000,
        guild_healing: 1_410_000,
        reference_healing: 1_120_000,
        duration_delta_percent: pct(214, 168)
      },
      {
        name: 'Gruul the Dragonkiller',
        guild_duration_ms: 289_000,
        reference_duration_ms: 231_000,
        guild_damage: 6_020_000,
        reference_damage: 5_890_000,
        guild_healing: 1_960_000,
        reference_healing: 1_540_000,
        duration_delta_percent: pct(289, 231)
      }
    ]
  }
};
