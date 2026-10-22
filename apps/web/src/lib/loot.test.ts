import { describe, expect, it } from 'vitest';
import { ApiError } from './api';
import { hubLoot, itemFacts, lootError, ordinal, qualityName, shifted, wowheadItem } from './loot';
import { previewLoot } from './preview/loot-fake';

describe('loot priority', () => {
  it('links an item to its Wowhead page by id', () => {
    expect(wowheadItem(19019)).toBe('https://www.wowhead.com/classic/item=19019');
  });

  it('says ranks the way officers do', () => {
    expect([1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 101].map(ordinal)).toEqual([
      '1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '22nd', '23rd', '101st'
    ]);
  });

  it('names qualities and slots', () => {
    expect(qualityName(4)).toBe('Epic');
    expect(qualityName(-1)).toBe('');
    expect(itemFacts({ slot: 'INVTYPE_2HWEAPON', item_level: 80 })).toBe('Two-hand · item level 80');
    expect(itemFacts({ slot: 'INVTYPE_NON_EQUIP_IGNORE', item_level: 60 })).toBe('item level 60');
    expect(itemFacts({ slot: '', item_level: -1 })).toBe('');
  });

  it('moves one member up or down the line, and not past either end', () => {
    expect(shifted([1, 2, 3], 3, -1)).toEqual([1, 3, 2]);
    expect(shifted([1, 2, 3], 1, 1)).toEqual([2, 1, 3]);
    expect(shifted([1, 2, 3], 1, -1)).toEqual([1, 2, 3]);
    expect(shifted([1, 2, 3], 3, 1)).toEqual([1, 2, 3]);
    expect(shifted([1, 2, 3], 9, 1)).toEqual([1, 2, 3]);
  });

  it('turns refusals into words for officers', () => {
    expect(lootError(new Error('x'))).toBe('Something went wrong; try again.');
    expect(lootError(new ApiError(401, ''))).toMatch(/Sign in/);
    expect(lootError(new ApiError(403, ''))).toMatch(/officers/);
    expect(lootError(new ApiError(404, 'That item is not on this night’s loot list'))).toMatch(/not on this night/);
    expect(lootError(new ApiError(404, ''))).toMatch(/refreshed/);
    expect(lootError(new ApiError(409, 'Already on the list'))).toBe('Already on the list');
    expect(lootError(new ApiError(500, ''))).toBe('Something went wrong; try again.');
  });

  it('calls the hub under the night', async () => {
    const calls: [string, RequestInit | undefined][] = [];
    const f = (async (path: string, init?: RequestInit) => {
      calls.push([path, init]);
      return new Response(init?.method === 'DELETE' ? null : '{}', { status: init?.method === 'DELETE' ? 204 : 200 });
    }) as typeof fetch;
    const hub = hubLoot(f);
    await hub.loot('wed');
    await hub.search('wed', 'head of ony');
    await hub.add('wed', 19019);
    await hub.note('wed', 4, 'Bindings first');
    await hub.line('wed', 4, [2, 1]);
    await hub.received('wed', 4, 2, true);
    await hub.remove('wed', 4);
    expect(calls.map(([p, i]) => `${i?.method ?? 'GET'} ${p}`)).toEqual([
      'GET /api/days/wed/loot',
      'GET /api/days/wed/loot/items?q=head%20of%20ony',
      'POST /api/days/wed/loot',
      'PUT /api/days/wed/loot/4',
      'PUT /api/days/wed/loot/4/line',
      'PUT /api/days/wed/loot/4/line/2/received',
      'DELETE /api/days/wed/loot/4'
    ]);
    expect(JSON.parse(String(calls[4][1]?.body))).toEqual({ member_ids: [2, 1] });
    expect(JSON.parse(String(calls[5][1]?.body))).toEqual({ received: true });
  });

  it('works in the preview: add, rank, mark received, take off', async () => {
    const night = await previewLoot.loot('sun');
    expect(night.items).toEqual([]);
    const [found] = await previewLoot.search('sun', 'sulfuras hand');
    const entry = await previewLoot.add('sun', found.id);
    await expect(previewLoot.add('sun', found.id)).rejects.toBeInstanceOf(ApiError);
    await expect(previewLoot.search('sun', 's')).rejects.toBeInstanceOf(ApiError);
    let line = await previewLoot.line('sun', entry.id, [3, 1]);
    expect(line.recipients.map((r) => [r.rank, r.member_id, r.next_up])).toEqual([[1, 3, true], [2, 1, false]]);
    line = await previewLoot.received('sun', entry.id, 3, true);
    expect(line.recipients.find((r) => r.next_up)?.member_id).toBe(1);
    line = await previewLoot.note('sun', entry.id, ' For the tank ');
    expect(line.note).toBe('For the tank');
    line = await previewLoot.received('sun', entry.id, 3, false);
    expect(line.recipients[0].next_up).toBe(true);
    await previewLoot.remove('sun', entry.id);
    await expect(previewLoot.remove('sun', entry.id)).rejects.toBeInstanceOf(ApiError);
    expect((await previewLoot.loot('wed')).items[0].recipients[1].next_up).toBe(true);
  });
});
