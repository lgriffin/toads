/**
 * The preview's loot lists: a handful of sample items in the browser only, so a night's loot section works on GitHub
 * Pages with no hub behind it. Changes last until the page reloads.
 */
import { ApiError } from '$lib/api';
import type { CatalogueItem, LootBackend, LootEntry, NightLoot } from '$lib/loot';
import { PREVIEW_MEMBERS } from './awards-fake';

const CATALOGUE: CatalogueItem[] = [
  { id: 19019, name: 'Thunderfury, Blessed Blade of the Windseeker', quality: 5, item_level: 80, slot: 'INVTYPE_WEAPON' },
  { id: 17182, name: 'Sulfuras, Hand of Ragnaros', quality: 5, item_level: 80, slot: 'INVTYPE_2HWEAPON' },
  { id: 18814, name: 'Choker of the Fire Lord', quality: 4, item_level: 78, slot: 'INVTYPE_NECK' },
  { id: 17076, name: "Bonereaver's Edge", quality: 4, item_level: 77, slot: 'INVTYPE_2HWEAPON' },
  { id: 18423, name: 'Head of Onyxia', quality: 4, item_level: 60, slot: 'INVTYPE_NON_EQUIP_IGNORE' },
  { id: 17204, name: 'Eye of Sulfuras', quality: 5, item_level: 60, slot: 'INVTYPE_NON_EQUIP_IGNORE' },
  { id: 18608, name: 'Benediction', quality: 4, item_level: 75, slot: 'INVTYPE_2HWEAPON' },
  { id: 16922, name: 'Leggings of Transcendence', quality: 4, item_level: 76, slot: 'INVTYPE_LEGS' }
];

let nextId = 1;
const lists: Record<string, LootEntry[]> = {
  wed: [entry(19019, 'Bindings first; the Eye goes to the same raider.', [2, 1, 3], [2]), entry(18814, '', [4], [])]
};

function entry(itemId: number, note: string, line: number[], received: number[], id = nextId++): LootEntry {
  const item = CATALOGUE.find((i) => i.id === itemId)!;
  const firstWaiting = line.find((m) => !received.includes(m));
  return {
    id,
    item_id: item.id,
    item_name: item.name,
    quality: item.quality,
    item_level: item.item_level,
    slot: item.slot,
    note,
    recipients: line.map((member_id, i) => ({
      member_id,
      rank: i + 1,
      name: PREVIEW_MEMBERS.find((m) => m.member_id === member_id)?.display_name ?? '',
      received_at: received.includes(member_id) ? '2026-10-21T21:30:00Z' : null,
      next_up: member_id === firstWaiting
    })),
    updated_at: new Date().toISOString()
  };
}

function find(day: string, id: number): LootEntry {
  const found = (lists[day] ?? []).find((e) => e.id === id);
  if (!found) throw new ApiError(404, 'That item is not on this night’s loot list');
  return found;
}

function rebuild(day: string, old: LootEntry, note: string, line: number[], received: number[]): LootEntry {
  const updated = entry(old.item_id, note, line, received, old.id);
  lists[day] = lists[day].map((e) => (e.id === old.id ? updated : e));
  return updated;
}

const receivedIn = (e: LootEntry) => e.recipients.filter((r) => r.received_at).map((r) => r.member_id);

export const previewLoot: LootBackend = {
  async loot(day): Promise<NightLoot> {
    return {
      raid_day: day,
      items: (lists[day] ??= []),
      roster: PREVIEW_MEMBERS.map((m) => ({ member_id: m.member_id, name: m.display_name, wow_class: null })),
      catalogue: 'Preview sample of LibItemDB’s WoW Forever items'
    };
  },
  async search(_day, query) {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean);
    if (query.trim().length < 2) throw new ApiError(422, 'Type at least two letters');
    return CATALOGUE.filter((i) => words.every((w) => i.name.toLowerCase().includes(w))).sort((a, b) => b.quality - a.quality);
  },
  async add(day, itemId, note = '') {
    if ((lists[day] ??= []).some((e) => e.item_id === itemId)) throw new ApiError(409, 'That item is already on the list');
    const e = entry(itemId, note.trim(), [], []);
    lists[day].push(e);
    return e;
  },
  async note(day, id, note) {
    const old = find(day, id);
    return rebuild(day, old, note.trim(), old.recipients.map((r) => r.member_id), receivedIn(old));
  },
  async line(day, id, memberIds) {
    const old = find(day, id);
    return rebuild(day, old, old.note, memberIds, receivedIn(old).filter((m) => memberIds.includes(m)));
  },
  async received(day, id, memberId, received) {
    const old = find(day, id);
    const had = receivedIn(old).filter((m) => m !== memberId);
    return rebuild(day, old, old.note, old.recipients.map((r) => r.member_id), received ? [...had, memberId] : had);
  },
  async remove(day, id) {
    find(day, id);
    lists[day] = lists[day].filter((e) => e.id !== id);
  }
};
