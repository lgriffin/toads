/**
 * The preview's comp builder: a sample roster for each raid night and comps kept in the browser only, so the builder
 * works on GitHub Pages with no hub behind it. Changes last until the page reloads.
 */
import { ApiError } from '$lib/api';
import { fromSlots, type CompBackend, type PoolEntry, type SavedComp } from '$lib/comp';

// [name, class, primary, secondary]; a null class has not set their specs yet.
type Row = [string, string | null, string | null, string | null];

const WEDNESDAY: Row[] = [
  ['Hopscotch', 'shaman', 'shaman-elemental', 'shaman-restoration'],
  ['Lilypadd', 'shaman', 'shaman-restoration', 'shaman-elemental'],
  ['Ribbit', 'warrior', 'warrior-protection', 'warrior-fury'],
  ['Croak', 'warrior', 'warrior-fury', 'warrior-arms'],
  ['Bogwort', 'druid', 'druid-guardian', 'druid-feral'],
  ['Tadpole', 'priest', 'priest-holy', 'priest-discipline'],
  ['Duckweed', 'priest', 'priest-shadow', 'priest-holy'],
  ['Marshmallow', 'paladin', 'paladin-holy', 'paladin-retribution'],
  ['Puddlejump', 'paladin', 'paladin-protection', 'paladin-holy'],
  ['Reedling', 'mage', 'mage-frost', 'mage-fire'],
  ['Mirewhisper', 'mage', 'mage-fire', null],
  ['Sludgefoot', 'warlock', 'warlock-destruction', 'warlock-affliction'],
  ['Wartsworth', 'warlock', 'warlock-affliction', null],
  ['Fenhopper', 'hunter', 'hunter-marksmanship', 'hunter-beast-mastery'],
  ['Cattail', 'hunter', 'hunter-beast-mastery', null],
  ['Pondscum', 'rogue', 'rogue-combat', 'rogue-assassination'],
  ['Ripple', 'rogue', 'rogue-assassination', null],
  ['Mudskip', 'druid', 'druid-restoration', 'druid-balance'],
  ['Moonfrog', 'druid', 'druid-balance', 'druid-restoration'],
  ['Galewart', 'shaman', 'shaman-enhancement', 'shaman-elemental'],
  ['Bulrush', null, null, null],
  ['Lotus', null, null, null]
];

const SUNDAY: Row[] = [
  ['Hopscotch', 'shaman', 'shaman-elemental', 'shaman-restoration'],
  ['Bogwort', 'druid', 'druid-guardian', 'druid-feral'],
  ['Stillwater', 'warrior', 'warrior-protection', null],
  ['Mosshide', 'priest', 'priest-holy', null],
  ['Kelpie', 'mage', 'mage-arcane', 'mage-frost'],
  ['Siltstrider', 'hunter', 'hunter-survival', 'hunter-marksmanship'],
  ['Brookling', 'paladin', 'paladin-retribution', 'paladin-holy'],
  ['Lagoon', null, null, null]
];

const IDS = new Map<string, number>();
const idOf = (name: string) => {
  if (!IDS.has(name)) IDS.set(name, IDS.size + 1);
  return IDS.get(name)!;
};

const entries = (rows: Row[]): PoolEntry[] =>
  rows
    .map(([name, wow_class, primary, secondary]) => ({ member_id: idOf(name), name, wow_class, primary, secondary }))
    .sort((a, b) => a.name.localeCompare(b.name));

const POOLS: Record<string, PoolEntry[]> = { wed: entries(WEDNESDAY), sun: entries(SUNDAY) };
const NAMES = new Map([...IDS].map(([name, id]) => [id, name]));

let saved: SavedComp[] = [];
let nextId = 1;

export const previewComps: CompBackend = {
  pool: async (day) => POOLS[day] ?? [],
  comps: async (day) => saved.filter((c) => c.raid_day === day),
  async save(day, id, name, slots) {
    const clean = name.trim();
    if (saved.some((c) => c.raid_day === day && c.name === clean && c.id !== id))
      throw new ApiError(409, `This raid day already has a comp called ${clean}`);
    const comp: SavedComp = {
      id: id ?? nextId++,
      raid_day: day,
      name: clean,
      size: slots.length,
      slots: fromSlots(slots).map((s) => (s ? { ...s, member_name: s.member_id ? (NAMES.get(s.member_id) ?? null) : null } : null)),
      updated_by: 'Hopscotch',
      updated_at: new Date().toISOString()
    };
    saved = [...saved.filter((c) => c.id !== comp.id), comp];
    return comp;
  },
  async remove(_day, id) {
    saved = saved.filter((c) => c.id !== id);
  }
};
