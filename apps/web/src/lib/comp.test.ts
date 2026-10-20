import { describe, expect, it } from 'vitest';
import {
  BUFFS,
  CLASSES,
  SPECS,
  classCounts,
  clear,
  coverage,
  emptySlots,
  fromSlots,
  groupBuffs,
  groupCount,
  matches,
  otherSpec,
  place,
  resize,
  roleCounts,
  seatFor,
  seatOnto,
  specLabel,
  swap,
  toSlots,
  type PoolEntry,
  type Slots
} from './comp';

const ele: PoolEntry = { member_id: 1, name: 'Hopscotch', wow_class: 'shaman', primary: 'shaman-elemental', secondary: 'shaman-restoration', signed_in: true };
const resto: PoolEntry = { member_id: 2, name: 'Lilypadd', wow_class: 'shaman', primary: 'shaman-restoration', secondary: 'shaman-elemental', signed_in: true };
const enh: PoolEntry = { member_id: 3, name: 'Galewart', wow_class: 'shaman', primary: 'shaman-enhancement', secondary: null, signed_in: true };
const tank: PoolEntry = { member_id: 4, name: 'Ribbit', wow_class: 'warrior', primary: 'warrior-protection', secondary: 'warrior-fury', signed_in: true };

const seat = (spec: string, memberId: number | null = null) => ({ spec, memberId });

describe('the catalogue', () => {
  it('gives every class its specs and every spec a known class', () => {
    const classes = new Set(CLASSES.map((c) => c.id));
    expect(new Set(SPECS.map((s) => s.wowClass))).toEqual(classes);
    expect(new Set(SPECS.map((s) => s.id)).size).toBe(SPECS.length);
    for (const s of SPECS) expect(s.id.startsWith(`${s.wowClass}-`)).toBe(true);
  });

  it('only names classes and specs it has as buff providers', () => {
    const classes = new Set(CLASSES.map((c) => c.id));
    const specs = new Map(SPECS.map((s) => [s.id, s]));
    for (const b of BUFFS)
      for (const p of b.providers) {
        expect(classes, b.id).toContain(p.wowClass);
        if (p.spec) expect(specs.get(p.spec)?.wowClass, b.id).toBe(p.wowClass);
      }
    expect(new Set(BUFFS.map((b) => b.id)).size).toBe(BUFFS.length);
  });

  it('labels a spec with its class', () => {
    expect(specLabel('shaman-elemental')).toBe('Elemental Shaman');
    expect(specLabel('nope')).toBe('');
  });
});

describe('seating', () => {
  it('splits 10, 20 and 40 into groups of five', () => {
    expect([10, 20, 40].map(groupCount)).toEqual([2, 4, 8]);
  });

  it('moves a member rather than seating them twice', () => {
    let slots = place(emptySlots(10), 0, seat('shaman-elemental', 1));
    slots = place(slots, 6, seat('shaman-restoration', 1));
    expect(slots[0]).toBeNull();
    expect(slots[6]).toEqual(seat('shaman-restoration', 1));
  });

  it('lets the same spec with no name fill many seats', () => {
    let slots = emptySlots(10);
    for (const i of [0, 1, 2]) slots = place(slots, i, seat('mage-frost'));
    expect(slots.filter(Boolean)).toHaveLength(3);
  });

  it('swaps two seats, moves onto an empty one, and clears', () => {
    const slots: Slots = [seat('mage-frost'), null, seat('priest-holy'), null, null];
    expect(swap(slots, 0, 2).slice(0, 3)).toEqual([seat('priest-holy'), null, seat('mage-frost')]);
    expect(swap(slots, 0, 1).slice(0, 2)).toEqual([null, seat('mage-frost')]);
    expect(clear(slots, 2)[2]).toBeNull();
  });

  it('keeps the seats that fit when resized', () => {
    const slots = place(place(emptySlots(20), 2, seat('mage-fire')), 15, seat('rogue-combat'));
    const small = resize(slots, 10);
    expect(small).toHaveLength(10);
    expect(small[2]).toEqual(seat('mage-fire'));
    expect(resize(small, 40)).toHaveLength(40);
  });

  it('counts roles and classes', () => {
    const slots: Slots = [seat('warrior-protection'), seat('priest-holy'), seat('shaman-elemental'), seat('shaman-enhancement'), null];
    expect(roleCounts(slots)).toEqual({ tank: 1, healer: 1, melee: 1, ranged: 1 });
    expect(classCounts(slots).map((c) => [c.wowClass.id, c.count])).toEqual([['warrior', 1], ['priest', 1], ['shaman', 2]]);
  });

  it('round-trips through the hub shape', () => {
    const slots: Slots = [{ spec: 'mage-frost', memberId: 7, memberName: 'Reedling' }, null];
    const api = fromSlots(slots);
    expect(api).toEqual([{ spec: 'mage-frost', member_id: 7 }, null]);
    expect(toSlots({ slots: [{ ...api[0]!, member_name: 'Reedling' }, null] })).toEqual(slots);
  });
});

describe('buffs', () => {
  it('finds raid buffs anywhere and party buffs only in the provider group', () => {
    const slots = emptySlots(10);
    slots[0] = seat('paladin-holy');
    slots[7] = seat('warlock-destruction');
    const cover = coverage(slots);
    const kings = cover.find((c) => c.buff.id === 'kings')!;
    expect(kings.seats).toEqual([0]);
    const pact = cover.find((c) => c.buff.id === 'blood-pact')!;
    expect(pact.groups).toEqual([1]);
    expect(groupBuffs(cover, 0).map((b) => b.id)).toContain('devotion-aura');
    expect(groupBuffs(cover, 1).map((b) => b.id)).toEqual(['blood-pact']);
  });

  it('needs the talent spec for talent buffs', () => {
    const tide = (spec: string) => coverage([seat(spec)]).find((c) => c.buff.id === 'mana-tide')!.seats.length;
    expect(tide('shaman-restoration')).toBe(1);
    expect(tide('shaman-elemental')).toBe(0);
    const lotp = (spec: string) => coverage([seat(spec)]).find((c) => c.buff.id === 'leader-of-the-pack')!.seats.length;
    expect([lotp('druid-feral'), lotp('druid-guardian'), lotp('druid-balance')]).toEqual([1, 1, 0]);
  });

  it('shows an empty comp missing everything', () => {
    expect(coverage(emptySlots(10)).every((c) => c.seats.length === 0)).toBe(true);
  });
});

describe('the roster', () => {
  const pool = [ele, resto, enh, tank];

  it('finds a spec as a primary or a secondary', () => {
    expect(pool.filter((e) => matches(e, { spec: 'shaman-elemental' })).map((e) => e.name)).toEqual(['Hopscotch', 'Lilypadd']);
    expect(pool.filter((e) => matches(e, { spec: 'shaman-enhancement' })).map((e) => e.name)).toEqual(['Galewart']);
  });

  it('filters by class, role and name', () => {
    expect(pool.filter((e) => matches(e, { wowClass: 'warrior' }))).toEqual([tank]);
    expect(pool.filter((e) => matches(e, { role: 'healer' })).map((e) => e.name)).toEqual(['Hopscotch', 'Lilypadd']);
    expect(pool.filter((e) => matches(e, { query: ' lily ' }))).toEqual([resto]);
    expect(pool.filter((e) => matches(e, {}))).toEqual(pool);
  });

  it('seats a member as the spec filtered for, else their primary', () => {
    expect(seatFor(resto, { spec: 'shaman-elemental' })?.spec).toBe('shaman-elemental');
    expect(seatFor(resto)?.spec).toBe('shaman-restoration');
    expect(seatFor(tank, { role: 'melee' })?.spec).toBe('warrior-fury');
    expect(seatFor(enh, { spec: 'shaman-elemental' })?.spec).toBe('shaman-enhancement');
    expect(seatFor({ member_id: 9, name: 'Lotus', wow_class: null, primary: null, secondary: null, signed_in: true })).toBeNull();
  });

  it('seats a member without specs in a bare spec seat only', () => {
    const lotus: PoolEntry = { member_id: 9, name: 'Lotus', wow_class: null, primary: null, secondary: null, signed_in: false };
    expect(seatOnto(lotus, { spec: 'priest-holy', memberId: null })).toEqual({ spec: 'priest-holy', memberId: 9, memberName: 'Lotus' });
    expect(seatOnto(lotus, null)).toBeNull();
    expect(seatOnto(lotus, { spec: 'priest-holy', memberId: 1 })).toBeNull();
    expect(seatOnto(resto, { spec: 'priest-holy', memberId: null })?.spec).toBe('shaman-restoration');
  });

  it('offers the other spec a seated member plays', () => {
    expect(otherSpec({ spec: 'shaman-elemental', memberId: 1 }, pool)).toBe('shaman-restoration');
    expect(otherSpec({ spec: 'shaman-enhancement', memberId: 3 }, pool)).toBeNull();
    expect(otherSpec({ spec: 'mage-frost', memberId: 99 }, pool)).toBeNull();
  });
});
