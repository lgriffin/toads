/**
 * Officers' loot priority (docs/loot.md): each raid night's officers keep a list of the big-ticket items they decide on,
 * rank members of the night's raid group for each one (1st, 2nd, 3rd...) and mark each one received. The hub's routes
 * are under /api/days/{day}/loot and only that night's officers (and the global tier) may call them; this page only
 * hides the section from everyone else.
 */
import { ApiError, call, type Fetch } from './api';

export const NOTE_LIMIT = 500;
export const LINE_LIMIT = 10;
/** The hub refuses a search shorter than this. */
export const MIN_QUERY = 2;

/** One item from the hub's item catalogue: LibItemDB's WoW Forever items, with Classic's filling the gaps. */
export interface CatalogueItem {
  id: number;
  name: string;
  /** 0 poor, 1 common, 2 uncommon, 3 rare, 4 epic, 5 legendary; -1 when the catalogue no longer knows it. */
  quality: number;
  item_level: number;
  /** The game's equip slot, such as INVTYPE_HEAD; "" or INVTYPE_NON_EQUIP_IGNORE for an item nobody wears. */
  slot: string;
  /** "Forever", or "Vanilla" for an item only Classic's data has (Forever's beta data lacks much raid loot). */
  flavour?: string;
}

export interface InLine {
  member_id: number;
  /** From 1. */
  rank: number;
  name: string;
  received_at: string | null;
  /** First in line without the item: the one who gets the next drop. */
  next_up: boolean;
}

export interface LootEntry {
  id: number;
  item_id: number;
  /** The canonical name the item had when it was added. */
  item_name: string;
  quality: number;
  item_level: number;
  slot: string;
  note: string;
  recipients: InLine[];
  updated_at: string;
}

export interface RosterMember {
  member_id: number;
  name: string;
  wow_class: string | null;
}

export interface NightLoot {
  raid_day: string;
  items: LootEntry[];
  /** Who can be put in line: the night's raid group. */
  roster: RosterMember[];
  /** Where the item data comes from. */
  catalogue: string;
}

/** What the loot section talks to: the hub, or the preview's in-browser fake. */
export interface LootBackend {
  loot(day: string): Promise<NightLoot>;
  search(day: string, query: string): Promise<CatalogueItem[]>;
  add(day: string, itemId: number, note?: string): Promise<LootEntry>;
  note(day: string, id: number, note: string): Promise<LootEntry>;
  line(day: string, id: number, memberIds: number[]): Promise<LootEntry>;
  received(day: string, id: number, memberId: number, received: boolean): Promise<LootEntry>;
  remove(day: string, id: number): Promise<void>;
}

const base = (day: string) => `/api/days/${encodeURIComponent(day)}/loot`;
const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export function hubLoot(f: Fetch = fetch): LootBackend {
  return {
    loot: (day) => call<NightLoot>(f, base(day)),
    search: (day, query) => call<CatalogueItem[]>(f, `${base(day)}/items?q=${encodeURIComponent(query)}`),
    add: (day, itemId, note = '') => call<LootEntry>(f, base(day), json('POST', { item_id: itemId, note })),
    note: (day, id, note) => call<LootEntry>(f, `${base(day)}/${encodeURIComponent(id)}`, json('PUT', { note })),
    line: (day, id, memberIds) =>
      call<LootEntry>(f, `${base(day)}/${encodeURIComponent(id)}/line`, json('PUT', { member_ids: memberIds })),
    received: (day, id, memberId, received) =>
      call<LootEntry>(
        f,
        `${base(day)}/${encodeURIComponent(id)}/line/${encodeURIComponent(memberId)}/received`,
        json('PUT', { received })
      ),
    remove: (day, id) => call<void>(f, `${base(day)}/${encodeURIComponent(id)}`, { method: 'DELETE' })
  };
}

/** The item's page on Wowhead, where raiders look items up. Forever shares Classic's item ids. */
export function wowheadItem(itemId: number): string {
  return `https://www.wowhead.com/classic/item=${encodeURIComponent(itemId)}`;
}

const QUALITIES = ['Poor', 'Common', 'Uncommon', 'Rare', 'Epic', 'Legendary', 'Artifact', 'Heirloom'];

/** "Epic", for a quality number; "" when unknown. */
export function qualityName(quality: number): string {
  return QUALITIES[quality] ?? '';
}

const SLOTS: Record<string, string> = {
  INVTYPE_HEAD: 'Head',
  INVTYPE_NECK: 'Neck',
  INVTYPE_SHOULDER: 'Shoulder',
  INVTYPE_BODY: 'Shirt',
  INVTYPE_CHEST: 'Chest',
  INVTYPE_ROBE: 'Chest',
  INVTYPE_WAIST: 'Waist',
  INVTYPE_LEGS: 'Legs',
  INVTYPE_FEET: 'Feet',
  INVTYPE_WRIST: 'Wrist',
  INVTYPE_HAND: 'Hands',
  INVTYPE_FINGER: 'Finger',
  INVTYPE_TRINKET: 'Trinket',
  INVTYPE_CLOAK: 'Back',
  INVTYPE_WEAPON: 'One-hand',
  INVTYPE_SHIELD: 'Shield',
  INVTYPE_2HWEAPON: 'Two-hand',
  INVTYPE_WEAPONMAINHAND: 'Main hand',
  INVTYPE_WEAPONOFFHAND: 'Off hand',
  INVTYPE_HOLDABLE: 'Held in off hand',
  INVTYPE_RANGED: 'Ranged',
  INVTYPE_RANGEDRIGHT: 'Ranged',
  INVTYPE_THROWN: 'Thrown',
  INVTYPE_RELIC: 'Relic',
  INVTYPE_TABARD: 'Tabard',
  INVTYPE_BAG: 'Bag',
  INVTYPE_QUIVER: 'Quiver',
  INVTYPE_AMMO: 'Ammo'
};

/** "Two-hand · item level 80", for an item's line under its name. */
export function itemFacts(item: Pick<CatalogueItem, 'slot' | 'item_level'>): string {
  const parts = [SLOTS[item.slot] ?? '', item.item_level > 0 ? `item level ${item.item_level}` : ''];
  return parts.filter(Boolean).join(' · ');
}

/** "1st", "2nd", "3rd", "4th"... for a rank. */
export function ordinal(rank: number): string {
  const tens = rank % 100;
  if (tens >= 11 && tens <= 13) return `${rank}th`;
  return `${rank}${{ 1: 'st', 2: 'nd', 3: 'rd' }[rank % 10] ?? 'th'}`;
}

/** The line's member ids after moving `memberId` one place up (-1) or down (+1); unchanged at either end. */
export function shifted(ids: number[], memberId: number, by: -1 | 1): number[] {
  const i = ids.indexOf(memberId);
  const j = i + by;
  if (i < 0 || j < 0 || j >= ids.length) return ids;
  const out = [...ids];
  [out[i], out[j]] = [out[j], out[i]];
  return out;
}

/** What to tell an officer when a loot call fails. */
export function lootError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Sign in again to use the loot list.';
    case 403:
      return 'Only this raid night’s officers can use its loot list.';
    case 404:
      return e.message || 'That item is gone; someone may have removed it. The list has been refreshed.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}
