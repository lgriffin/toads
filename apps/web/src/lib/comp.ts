/**
 * The officers' comp builder (docs/comps.md): classes and specs, the buffs and debuffs each brings in World of
 * Warcraft: Forever, and the rules for seating a raid in groups of five. The hub's catalogue lives in
 * services/api/src/toads_api/comps/catalog.py; services/api/tests/test_comps.py fails if the two drift apart.
 */
import { ApiError, call, type Fetch } from './api';
import { dayName } from './absences';

export type Role = 'tank' | 'healer' | 'melee' | 'ranged';

export const ROLES: readonly { id: Role; label: string }[] = [
  { id: 'tank', label: 'Tanks' },
  { id: 'healer', label: 'Healers' },
  { id: 'melee', label: 'Melee' },
  { id: 'ranged', label: 'Ranged' }
];

export interface WowClass {
  id: string;
  name: string;
  /** The class colour players know from the game's raid frames. */
  colour: string;
}

export const CLASSES: readonly WowClass[] = [
  { id: 'warrior', name: 'Warrior', colour: '#c79c6e' },
  { id: 'paladin', name: 'Paladin', colour: '#f58cba' },
  { id: 'hunter', name: 'Hunter', colour: '#abd473' },
  { id: 'rogue', name: 'Rogue', colour: '#fff569' },
  { id: 'priest', name: 'Priest', colour: '#ffffff' },
  { id: 'shaman', name: 'Shaman', colour: '#0070de' },
  { id: 'mage', name: 'Mage', colour: '#69ccf0' },
  { id: 'warlock', name: 'Warlock', colour: '#9482c9' },
  { id: 'druid', name: 'Druid', colour: '#ff7d0a' }
];

export interface Spec {
  id: string;
  wowClass: string;
  name: string;
  role: Role;
}

/** Every spec, in the hub's catalogue order. Ids are stored, so never rename one. */
export const SPECS: readonly Spec[] = [
  { id: 'warrior-arms', wowClass: 'warrior', name: 'Arms', role: 'melee' },
  { id: 'warrior-fury', wowClass: 'warrior', name: 'Fury', role: 'melee' },
  { id: 'warrior-protection', wowClass: 'warrior', name: 'Protection', role: 'tank' },
  { id: 'paladin-holy', wowClass: 'paladin', name: 'Holy', role: 'healer' },
  { id: 'paladin-protection', wowClass: 'paladin', name: 'Protection', role: 'tank' },
  { id: 'paladin-retribution', wowClass: 'paladin', name: 'Retribution', role: 'melee' },
  { id: 'hunter-beast-mastery', wowClass: 'hunter', name: 'Beast Mastery', role: 'ranged' },
  { id: 'hunter-marksmanship', wowClass: 'hunter', name: 'Marksmanship', role: 'ranged' },
  { id: 'hunter-survival', wowClass: 'hunter', name: 'Survival', role: 'ranged' },
  { id: 'rogue-assassination', wowClass: 'rogue', name: 'Assassination', role: 'melee' },
  { id: 'rogue-combat', wowClass: 'rogue', name: 'Combat', role: 'melee' },
  { id: 'rogue-subtlety', wowClass: 'rogue', name: 'Subtlety', role: 'melee' },
  { id: 'priest-discipline', wowClass: 'priest', name: 'Discipline', role: 'healer' },
  { id: 'priest-holy', wowClass: 'priest', name: 'Holy', role: 'healer' },
  { id: 'priest-shadow', wowClass: 'priest', name: 'Shadow', role: 'ranged' },
  { id: 'shaman-elemental', wowClass: 'shaman', name: 'Elemental', role: 'ranged' },
  { id: 'shaman-enhancement', wowClass: 'shaman', name: 'Enhancement', role: 'melee' },
  { id: 'shaman-restoration', wowClass: 'shaman', name: 'Restoration', role: 'healer' },
  { id: 'mage-arcane', wowClass: 'mage', name: 'Arcane', role: 'ranged' },
  { id: 'mage-fire', wowClass: 'mage', name: 'Fire', role: 'ranged' },
  { id: 'mage-frost', wowClass: 'mage', name: 'Frost', role: 'ranged' },
  { id: 'warlock-affliction', wowClass: 'warlock', name: 'Affliction', role: 'ranged' },
  { id: 'warlock-demonology', wowClass: 'warlock', name: 'Demonology', role: 'ranged' },
  { id: 'warlock-destruction', wowClass: 'warlock', name: 'Destruction', role: 'ranged' },
  { id: 'druid-balance', wowClass: 'druid', name: 'Balance', role: 'ranged' },
  { id: 'druid-feral', wowClass: 'druid', name: 'Feral', role: 'melee' },
  { id: 'druid-guardian', wowClass: 'druid', name: 'Guardian', role: 'tank' },
  { id: 'druid-restoration', wowClass: 'druid', name: 'Restoration', role: 'healer' }
];

const SPEC_BY_ID = new Map(SPECS.map((s) => [s.id, s]));
const CLASS_BY_ID = new Map(CLASSES.map((c) => [c.id, c]));

export const specOf = (id: string | null | undefined): Spec | undefined => (id ? SPEC_BY_ID.get(id) : undefined);
export const classOf = (id: string | null | undefined): WowClass | undefined => (id ? CLASS_BY_ID.get(id) : undefined);
export const specsOfClass = (wowClass: string): Spec[] => SPECS.filter((s) => s.wowClass === wowClass);

/** "Elemental Shaman". */
export function specLabel(id: string | null | undefined): string {
  const s = specOf(id);
  return s ? `${s.name} ${classOf(s.wowClass)?.name ?? ''}`.trim() : '';
}

// ------------------------------------------------------------------------------------------------ buffs

/** raid: everyone in the raid; party: the provider's group of five; target: one enemy or one friend. */
export type Scope = 'raid' | 'party' | 'target';

export type Category = 'stats' | 'ap' | 'spell' | 'resist' | 'utility' | 'armor' | 'spell-damage' | 'enemy-melee';

export const CATEGORY_LABEL: Record<Category, string> = {
  stats: 'Stats',
  ap: 'Attack power',
  spell: 'Mana and spell',
  resist: 'Resistances',
  utility: 'Utility',
  armor: 'Armor',
  'spell-damage': 'Spell damage',
  'enemy-melee': 'Enemy melee'
};

export interface Provider {
  wowClass: string;
  /** Only this spec brings it (a deep talent); every spec of the class when missing. */
  spec?: string;
  /** How, when it is not the obvious spell: a pet, a totem, an aura. */
  via?: string;
}

export interface Buff {
  id: string;
  name: string;
  scope: Scope;
  category: Category;
  providers: readonly Provider[];
  /** A stacking rule officers should know. */
  note?: string;
}

/**
 * What each class and spec brings to a Forever raid, from the beta client (October 2026). Forever made most class
 * buffs raid-wide: Prayer of Fortitude, Gift of the Wild, Arcane Brilliance and the shaman totems reach every group.
 */
export const BUFFS: readonly Buff[] = [
  { id: 'kings', name: 'Blessing of Kings', scope: 'raid', category: 'stats', providers: [{ wowClass: 'paladin' }] },
  { id: 'fortitude', name: 'Power Word: Fortitude', scope: 'raid', category: 'stats', providers: [{ wowClass: 'priest' }] },
  { id: 'mark-of-the-wild', name: 'Mark of the Wild', scope: 'raid', category: 'stats', providers: [{ wowClass: 'druid' }] },
  { id: 'strength-of-earth', name: 'Strength of Earth Totem', scope: 'raid', category: 'stats', providers: [{ wowClass: 'shaman' }] },
  {
    id: 'grace-of-air',
    name: 'Grace of Air Totem',
    scope: 'raid',
    category: 'stats',
    providers: [{ wowClass: 'shaman' }],
    note: 'Shares the air totem with Windfury, even across shamans.'
  },
  { id: 'moonkin-aura', name: 'Moonkin Aura', scope: 'raid', category: 'stats', providers: [{ wowClass: 'druid', spec: 'druid-balance' }] },
  {
    id: 'leader-of-the-pack',
    name: 'Leader of the Pack',
    scope: 'raid',
    category: 'stats',
    providers: [{ wowClass: 'druid', spec: 'druid-feral' }, { wowClass: 'druid', spec: 'druid-guardian' }]
  },
  { id: 'devotion-aura', name: 'Devotion Aura', scope: 'party', category: 'stats', providers: [{ wowClass: 'paladin' }] },
  { id: 'blood-pact', name: 'Blood Pact', scope: 'party', category: 'stats', providers: [{ wowClass: 'warlock', via: 'Imp' }] },
  { id: 'dark-inspiration', name: 'Dark Inspiration', scope: 'party', category: 'stats', providers: [{ wowClass: 'priest', spec: 'priest-shadow' }] },
  { id: 'might', name: 'Blessing of Might', scope: 'raid', category: 'ap', providers: [{ wowClass: 'paladin' }] },
  { id: 'battle-shout', name: 'Battle Shout', scope: 'raid', category: 'ap', providers: [{ wowClass: 'warrior' }] },
  { id: 'trueshot-aura', name: 'Trueshot Aura', scope: 'raid', category: 'ap', providers: [{ wowClass: 'hunter', spec: 'hunter-marksmanship' }] },
  {
    id: 'windfury',
    name: 'Windfury Totem',
    scope: 'raid',
    category: 'ap',
    providers: [{ wowClass: 'shaman' }],
    note: 'Shares the air totem with Grace of Air, and does not stack with Flametongue Totem.'
  },
  { id: 'furious-howl', name: 'Furious Howl', scope: 'raid', category: 'ap', providers: [{ wowClass: 'hunter', via: 'wolf pet' }] },
  { id: 'wisdom', name: 'Blessing of Wisdom', scope: 'raid', category: 'spell', providers: [{ wowClass: 'paladin' }] },
  { id: 'arcane-intellect', name: 'Arcane Intellect', scope: 'raid', category: 'spell', providers: [{ wowClass: 'mage' }] },
  { id: 'divine-spirit', name: 'Divine Spirit', scope: 'raid', category: 'spell', providers: [{ wowClass: 'priest' }] },
  { id: 'mana-spring', name: 'Mana Spring Totem', scope: 'party', category: 'spell', providers: [{ wowClass: 'shaman' }] },
  { id: 'mana-tide', name: 'Mana Tide Totem', scope: 'party', category: 'spell', providers: [{ wowClass: 'shaman', spec: 'shaman-restoration' }] },
  { id: 'salvation', name: 'Blessing of Salvation', scope: 'raid', category: 'utility', providers: [{ wowClass: 'paladin' }] },
  { id: 'light', name: 'Blessing of Light', scope: 'raid', category: 'utility', providers: [{ wowClass: 'paladin' }] },
  { id: 'tremor', name: 'Tremor Totem', scope: 'party', category: 'utility', providers: [{ wowClass: 'shaman' }] },
  { id: 'vampiric-embrace', name: 'Vampiric Embrace', scope: 'party', category: 'utility', providers: [{ wowClass: 'priest', spec: 'priest-shadow' }] },
  { id: 'concentration-aura', name: 'Concentration Aura', scope: 'party', category: 'utility', providers: [{ wowClass: 'paladin' }] },
  {
    id: 'fire-resistance',
    name: 'Fire Resistance',
    scope: 'raid',
    category: 'resist',
    providers: [{ wowClass: 'paladin', via: 'aura' }, { wowClass: 'shaman', via: 'totem' }]
  },
  {
    id: 'frost-resistance',
    name: 'Frost Resistance',
    scope: 'raid',
    category: 'resist',
    providers: [{ wowClass: 'paladin', via: 'aura' }, { wowClass: 'shaman', via: 'totem' }]
  },
  {
    id: 'nature-resistance',
    name: 'Nature Resistance',
    scope: 'raid',
    category: 'resist',
    providers: [{ wowClass: 'hunter', via: 'Aspect of the Wild' }, { wowClass: 'shaman', via: 'totem' }]
  },
  {
    id: 'shadow-resistance',
    name: 'Shadow Resistance',
    scope: 'raid',
    category: 'resist',
    providers: [{ wowClass: 'paladin', via: 'aura' }, { wowClass: 'priest', via: 'Prayer of Shadow Protection' }]
  },
  { id: 'sunder-armor', name: 'Sunder Armor', scope: 'target', category: 'armor', providers: [{ wowClass: 'warrior' }] },
  {
    id: 'expose-armor',
    name: 'Expose Armor',
    scope: 'target',
    category: 'armor',
    providers: [{ wowClass: 'rogue' }],
    note: 'Did not stack with Sunder Armor in Classic; Forever has not said.'
  },
  { id: 'faerie-fire', name: 'Faerie Fire', scope: 'target', category: 'armor', providers: [{ wowClass: 'druid' }] },
  {
    id: 'curse-of-recklessness',
    name: 'Curse of Recklessness',
    scope: 'target',
    category: 'armor',
    providers: [{ wowClass: 'warlock' }],
    note: 'One curse per warlock.'
  },
  {
    id: 'curse-of-the-elements',
    name: 'Curse of the Elements',
    scope: 'target',
    category: 'spell-damage',
    providers: [{ wowClass: 'warlock' }],
    note: 'Covers every magic school in Forever. One curse per warlock.'
  },
  { id: 'judgement-of-the-crusader', name: 'Judgement of the Crusader', scope: 'target', category: 'spell-damage', providers: [{ wowClass: 'paladin' }] },
  {
    id: 'demoralize',
    name: 'Attack power reduction',
    scope: 'target',
    category: 'enemy-melee',
    providers: [
      { wowClass: 'warrior', via: 'Demoralizing Shout' },
      { wowClass: 'druid', via: 'Demoralizing Roar' },
      { wowClass: 'paladin', spec: 'paladin-retribution', via: 'Vindication' }
    ]
  },
  { id: 'thunder-clap', name: 'Thunder Clap', scope: 'target', category: 'enemy-melee', providers: [{ wowClass: 'warrior' }] },
  { id: 'insect-swarm', name: 'Insect Swarm', scope: 'target', category: 'enemy-melee', providers: [{ wowClass: 'druid', spec: 'druid-balance' }] },
  { id: 'judgement-of-wisdom', name: 'Judgement of Wisdom', scope: 'target', category: 'utility', providers: [{ wowClass: 'paladin' }] },
  { id: 'power-infusion', name: 'Power Infusion', scope: 'target', category: 'spell', providers: [{ wowClass: 'priest', spec: 'priest-discipline' }] },
  { id: 'innervate', name: 'Innervate', scope: 'target', category: 'spell', providers: [{ wowClass: 'druid' }] }
];

// ------------------------------------------------------------------------------------------------ seats

export const RAID_SIZES = [10, 20, 40] as const;
export type RaidSize = (typeof RAID_SIZES)[number];
export const GROUP_SIZE = 5;

/** A filled seat: a spec, and in roster mode the member playing it. */
export interface Seat {
  spec: string;
  memberId: number | null;
  memberName?: string | null;
}

export type Slots = (Seat | null)[];

export const emptySlots = (size: number): Slots => Array.from({ length: size }, () => null);

/** Grow or shrink a comp, keeping the seats that still fit. */
export function resize(slots: Slots, size: number): Slots {
  return Array.from({ length: size }, (_, i) => slots[i] ?? null);
}

export const groupCount = (size: number) => Math.ceil(size / GROUP_SIZE);
export const groupOf = (index: number) => Math.floor(index / GROUP_SIZE);

/** Seat `seat` at `index`. A member already seated elsewhere moves rather than sitting twice. */
export function place(slots: Slots, index: number, seat: Seat): Slots {
  const next = slots.map((s) => (seat.memberId !== null && s?.memberId === seat.memberId ? null : s));
  next[index] = seat;
  return next;
}

/** Drag one seat onto another: they swap, so dropping onto an empty seat is a move. */
export function swap(slots: Slots, from: number, to: number): Slots {
  const next = [...slots];
  [next[from], next[to]] = [next[to], next[from]];
  return next;
}

export function clear(slots: Slots, index: number): Slots {
  const next = [...slots];
  next[index] = null;
  return next;
}

export function roleCounts(slots: Slots): Record<Role, number> {
  const counts: Record<Role, number> = { tank: 0, healer: 0, melee: 0, ranged: 0 };
  for (const s of slots) {
    const spec = specOf(s?.spec);
    if (spec) counts[spec.role] += 1;
  }
  return counts;
}

export function classCounts(slots: Slots): { wowClass: WowClass; count: number }[] {
  return CLASSES.map((c) => ({ wowClass: c, count: slots.filter((s) => specOf(s?.spec)?.wowClass === c.id).length })).filter(
    (c) => c.count > 0
  );
}

const provides = (p: Provider, spec: Spec) => p.wowClass === spec.wowClass && (!p.spec || p.spec === spec.id);

export interface Coverage {
  buff: Buff;
  /** Seat indexes that bring it. */
  seats: number[];
  /** For a party buff, the groups (0-based) that have it. */
  groups: number[];
}

/** Every buff with the seats that bring it; a buff nobody brings has no seats. */
export function coverage(slots: Slots): Coverage[] {
  return BUFFS.map((buff) => {
    const seats = slots.flatMap((s, i) => {
      const spec = specOf(s?.spec);
      return spec && buff.providers.some((p) => provides(p, spec)) ? [i] : [];
    });
    return { buff, seats, groups: [...new Set(seats.map(groupOf))].sort((a, b) => a - b) };
  });
}

/** The party buffs a group has, by name. */
export function groupBuffs(cover: Coverage[], group: number): Buff[] {
  return cover.filter((c) => c.buff.scope === 'party' && c.groups.includes(group)).map((c) => c.buff);
}

// ------------------------------------------------------------------------------------------------ roster

/** A member on a raid day's roster, as GET /api/days/{day}/comps/pool lists them. */
export interface PoolEntry {
  member_id: number;
  name: string;
  /** Null until the member sets their specs on Me. */
  wow_class: string | null;
  primary: string | null;
  secondary: string | null;
  /** False for someone holding the night's Discord role who has never signed in to the hub, so has no specs. */
  signed_in: boolean;
}

/** What the roster is narrowed to: a class, a spec (matching a primary or secondary), and a name search. */
export interface PoolFilter {
  wowClass?: string;
  spec?: string;
  role?: Role;
  query?: string;
}

const specsOf = (e: PoolEntry) => [e.primary, e.secondary].filter((s): s is string => !!s);

export function matches(e: PoolEntry, f: PoolFilter): boolean {
  if (f.query && !e.name.toLocaleLowerCase().includes(f.query.trim().toLocaleLowerCase())) return false;
  if (f.wowClass && e.wow_class !== f.wowClass) return false;
  if (f.spec && !specsOf(e).includes(f.spec)) return false;
  if (f.role && !specsOf(e).some((s) => specOf(s)?.role === f.role)) return false;
  return true;
}

/** The spec a member takes when seated: the one filtered for if they play it, else their primary. */
export function seatFor(e: PoolEntry, f: PoolFilter = {}): Seat | null {
  const played = specsOf(e);
  const wanted =
    (f.spec && played.includes(f.spec) && f.spec) ||
    (f.role && played.find((s) => specOf(s)?.role === f.role)) ||
    e.primary;
  return wanted ? { spec: wanted, memberId: e.member_id, memberName: e.name } : null;
}

/**
 * The seat a member takes when dropped on `target`. Someone without specs (a role holder who has not signed in yet)
 * fills a seat that already holds a bare spec, so officers place the spec first; null when there is none to fill.
 */
export function seatOnto(e: PoolEntry, target: Seat | null, f: PoolFilter = {}): Seat | null {
  if (specsOf(e).length) return seatFor(e, f);
  return target && !target.memberId ? { spec: target.spec, memberId: e.member_id, memberName: e.name } : null;
}

/** The other spec a seated member plays, to switch to; null when they play one. */
export function otherSpec(seat: Seat, pool: readonly PoolEntry[]): string | null {
  const e = pool.find((p) => p.member_id === seat.memberId);
  if (!e) return null;
  return specsOf(e).find((s) => s !== seat.spec) ?? null;
}

// ------------------------------------------------------------------------------------------------ the hub

export interface MySpecs {
  wow_class: string;
  primary: string;
  secondary: string | null;
  /** True while the specs are an officer's Raid-Helper import the member has not confirmed or changed. */
  imported?: boolean;
}

export interface ApiSeat {
  spec: string;
  member_id: number | null;
  member_name?: string | null;
}

export interface SavedComp {
  id: number;
  raid_day: string;
  name: string;
  size: number;
  slots: (ApiSeat | null)[];
  updated_by: string | null;
  updated_at: string;
}

export const toSlots = (c: Pick<SavedComp, 'slots'>): Slots =>
  c.slots.map((s) => (s ? { spec: s.spec, memberId: s.member_id, memberName: s.member_name ?? null } : null));

export const fromSlots = (slots: Slots): (ApiSeat | null)[] =>
  slots.map((s) => (s ? { spec: s.spec, member_id: s.memberId } : null));

export const getMySpecs = (f: Fetch = fetch) => call<MySpecs | null>(f, '/api/me/specs');

export const saveMySpecs = (specs: MySpecs, f: Fetch = fetch) =>
  call<MySpecs>(f, '/api/me/specs', { method: 'PUT', body: JSON.stringify(specs) });

export const clearMySpecs = (f: Fetch = fetch) => call<void>(f, '/api/me/specs', { method: 'DELETE' });

/** The comp builder's calls, so the static preview can stand in for the hub. */
export interface CompBackend {
  pool(day: string): Promise<PoolEntry[]>;
  comps(day: string): Promise<SavedComp[]>;
  save(day: string, id: number | null, name: string, slots: Slots): Promise<SavedComp>;
  remove(day: string, id: number): Promise<void>;
}

const days = (day: string) => `/api/days/${encodeURIComponent(day)}/comps`;

export const hubComps = (f: Fetch = fetch): CompBackend => ({
  pool: (day) => call<PoolEntry[]>(f, `${days(day)}/pool`),
  comps: (day) => call<SavedComp[]>(f, days(day)),
  save: (day, id, name, slots) =>
    call<SavedComp>(f, id === null ? days(day) : `${days(day)}/${id}`, {
      method: id === null ? 'POST' : 'PUT',
      body: JSON.stringify({ name, size: slots.length, slots: fromSlots(slots) })
    }),
  remove: (day, id) => call<void>(f, `${days(day)}/${id}`, { method: 'DELETE' })
});

export function compError(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 401) return 'Sign in with Discord first.';
    if (e.status === 403) return 'Only that raid night’s officers can build its comps.';
    if (e.status === 409 || e.status === 422 || e.status === 404) return e.message;
  }
  return 'The hub could not be reached; try again.';
}

/** A raid day's name from its config id. */
export const dayLabel = (id: string) => dayName(id);
