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

export interface Announcement {
  title: string;
  body: string;
  author: string;
  posted: string;
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

export const announcements: Announcement[] = [
  {
    title: 'Vashj prep night',
    body: 'Bring fire resist for Hydross swaps and a stack of Flasks of Relentless Assault. Tainted core runners, check #tactics.',
    author: 'Ribbitz',
    posted: '2026-09-25T20:12:00Z'
  },
  {
    title: 'Bank requests open for Wednesday',
    body: 'Wednesday bank is restocked with Super Mana Potions and Elixirs of Major Agility. Request through the Bank page.',
    author: 'Croakley',
    posted: '2026-09-23T09:40:00Z'
  }
];

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
