import { describe as group, expect, it, vi } from 'vitest';
import {
  PROFESSIONS,
  crafterGroups,
  describe,
  getNightCrafters,
  hubProfessions,
  professionName,
  withProfession,
  type Crafter
} from './professions';
import { previewNightCrafters, previewProfessions } from './preview/professions-fake';

const crafter = (profession: string, member_name: string): Crafter => ({
  profession,
  member_id: member_name.length,
  member_name,
  skill: null,
  specialisation: null,
  note: null,
  designated_by: null,
  designated_at: '2026-10-21T00:00:00Z'
});

group('professions', () => {
  it('lists every profession once, secondaries last', () => {
    const ids = PROFESSIONS.map((p) => p.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(PROFESSIONS.filter((p) => p.secondary).map((p) => p.id)).toEqual(['cooking', 'first-aid', 'fishing']);
    expect(professionName('first-aid')).toBe('First Aid');
  });

  it('describes a profession with its skill and specialisation', () => {
    expect(describe({ profession: 'engineering', skill: 300, specialisation: 'gnomish' })).toBe(
      'Engineering 300 · Gnomish'
    );
    expect(describe({ profession: 'mining', skill: null, specialisation: null })).toBe('Mining');
  });

  it('filters members by a profession and groups crafters in catalogue order', () => {
    const members = [
      { member_id: 1, name: 'A', professions: [{ profession: 'mining', skill: null, specialisation: null }], crafter_for: [] },
      { member_id: 2, name: 'B', professions: [], crafter_for: [] }
    ];
    expect(withProfession(members, 'mining').map((m) => m.name)).toEqual(['A']);
    expect(withProfession(members, '')).toHaveLength(2);
    const groups = crafterGroups([crafter('tailoring', 'Lily'), crafter('alchemy', 'Hop')]);
    expect(groups.map((g) => g.profession.id)).toEqual(['alchemy', 'tailoring']);
  });

  it('calls the night routes, or the admin routes for the guild-wide view', async () => {
    const f = vi.fn(async () => new Response(JSON.stringify({ members: [], crafters: [] }), { status: 200 }));
    const hub = hubProfessions(f as unknown as typeof fetch);
    await hub.overview('wed');
    await hub.overview(null);
    await hub.name('wed', 'alchemy', 7, '');
    const calls = f.mock.calls as unknown as [string, RequestInit][];
    expect(calls.map((c) => c[0])).toEqual([
      '/api/days/wed/professions',
      '/api/admin/professions',
      '/api/days/wed/crafters/alchemy/7'
    ]);
    expect(calls[2][1].body).toBe(JSON.stringify({ note: null }));
  });

  it('the preview names only members of the night who list the profession', async () => {
    const preview = previewProfessions();
    await expect(preview.name('wed', 'mining', 3, '')).rejects.toThrow('not on this raid night');
    await expect(preview.name('wed', 'mining', 2, '')).rejects.toThrow('do not list');
    await preview.name('wed', 'tailoring', 2, 'Mooncloth bags');
    const night = await preview.overview('wed');
    expect(night.crafters.map((c) => c.member_name)).toEqual(['Hopscotch', 'Lilypadd']);
    expect(night.members.find((m) => m.name === 'Lilypadd')?.crafter_for[0].note).toBe('Mooncloth bags');
    await preview.unname('wed', 'tailoring', 2);
    expect((await preview.overview(null)).crafters).toHaveLength(1);
  });

  it('reads a night\'s guild crafters for the Raid page, and the preview keeps each night to its own', async () => {
    const f = vi.fn(async () => new Response('[]', { status: 200, headers: { 'content-type': 'application/json' } }));
    await getNightCrafters('wed', f as unknown as typeof fetch);
    expect((f.mock.calls[0] as unknown[])[0]).toBe('/api/days/wed/crafters');
    expect(crafterGroups(previewNightCrafters('wed')).map((g) => g.profession.id)).toEqual(['alchemy', 'tailoring']);
    expect(previewNightCrafters('sun').map((c) => c.member_name)).toEqual(['Ribbit']);
  });
});
