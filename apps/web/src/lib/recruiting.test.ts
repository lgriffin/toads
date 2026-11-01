import { describe, expect, it } from 'vitest';
import { ApiError } from './api';
import { SPECS } from './comp';
import type { RecruitmentNeed } from './community';
import { previewNeeds, previewPublicNeeds } from './preview/needs-fake';
import { findSpec, hubNeeds, needsError, nightGroups, nightSummary, picksOf, specLabel, specsLeft } from './recruiting';

const need = (over: Partial<RecruitmentNeed>): RecruitmentNeed => ({
  className: 'Shaman',
  spec: 'Restoration',
  role: 'Healer',
  priority: 'medium',
  raidDays: ['wed' as RecruitmentNeed['raidDays'][number]],
  ...over
});

describe('the homepage groups', () => {
  it('shows a group as full when its night lists nothing for it', () => {
    const groups = nightGroups([need({}), need({ className: 'Warrior', spec: 'Protection', role: 'Tank', raidDays: ['Sunday'] })], 'wed');
    expect(groups.map((g) => [g.id, g.open])).toEqual([
      ['tank', false],
      ['healer', true],
      ['damage', false]
    ]);
    expect(nightSummary(groups, 'Wednesday')).toBe('Wednesday is recruiting healers.');
  });

  it('puts melee and ranged under damage, by class in the order listed', () => {
    const groups = nightGroups(
      [
        need({ className: 'Priest', spec: 'Shadow', role: 'Ranged', priority: 'high' }),
        need({ className: 'Rogue', spec: 'Combat', role: 'Melee' }),
        need({ className: 'Priest', spec: 'Shadow', role: 'Ranged' })
      ],
      'wed'
    );
    const damage = groups[2];
    expect(damage.classes.map((c) => [c.name, c.specs])).toEqual([
      ['Priest', [{ name: 'Shadow', priority: 'high' }]],
      ['Rogue', [{ name: 'Combat', priority: 'medium' }]]
    ]);
    expect(nightSummary(groups, 'Wednesday')).toBe('Wednesday is recruiting damage dealers.');
  });

  it('says a night with nothing listed is full', () => {
    const groups = nightGroups([], 'thu');
    expect(groups.every((g) => !g.open)).toBe(true);
    expect(nightSummary(groups, 'Thursday')).toMatch(/^Thursday is full for now/);
    const all = nightGroups(
      [need({ role: 'Tank', className: 'Druid', spec: 'Guardian' }), need({}), need({ role: 'Melee', className: 'Rogue', spec: 'Combat' })],
      'wed'
    );
    expect(nightSummary(all, 'Wednesday')).toBe('Wednesday is recruiting tanks, healers and damage dealers.');
  });
});

describe('picking a spec', () => {
  it('matches a full label or a unique start of words', () => {
    expect(findSpec('restoration shaman', SPECS)?.id).toBe('shaman-restoration');
    expect(findSpec('  resto  sha ', SPECS)?.id).toBe('shaman-restoration');
    expect(findSpec('guardian', SPECS)?.id).toBe('druid-guardian');
    expect(findSpec('holy', SPECS)).toBeUndefined();
    expect(findSpec('', SPECS)).toBeUndefined();
    expect(specLabel(SPECS[0])).toBe('Arms Warrior');
  });

  it('offers only the specs not yet listed', () => {
    const left = specsLeft([{ spec_id: 'warrior-arms', class_name: 'Warrior', spec: 'Arms', role: 'Melee', priority: 'low' }]);
    expect(left.some((s) => s.id === 'warrior-arms')).toBe(false);
    expect(left).toHaveLength(SPECS.length - 1);
    expect(findSpec('holy pal', left)?.id).toBe('paladin-holy');
  });
});

describe('the hub and the preview', () => {
  it('saves a night’s whole list to its own route', async () => {
    const calls: [string, RequestInit | undefined][] = [];
    const f = (async (url: string, init?: RequestInit) => {
      calls.push([url, init]);
      return new Response(JSON.stringify({ raid_day: 'sun', needs: [] }), { status: 200 });
    }) as typeof fetch;
    await hubNeeds(f).save('sun', [{ spec_id: 'mage-fire', priority: 'high' }]);
    expect(calls[0][0]).toBe('/api/days/sun/admin/recruitment-needs');
    expect(calls[0][1]?.method).toBe('PUT');
    expect(JSON.parse(String(calls[0][1]?.body))).toEqual({ needs: [{ spec_id: 'mage-fire', priority: 'high' }] });
  });

  it('shows the preview officers’ change on the preview homepage', async () => {
    const backend = previewNeeds();
    const before = await backend.needs('thu');
    const saved = await backend.save('thu', [...picksOf(before.needs), { spec_id: 'paladin-protection', priority: 'high' }]);
    expect(saved.needs.at(-1)).toMatchObject({ class_name: 'Paladin', spec: 'Protection', role: 'Tank' });
    expect(nightGroups(previewPublicNeeds(), 'thu')[0].open).toBe(true);
    await expect(backend.save('thu', [{ spec_id: 'mage-fire', priority: 'low' }, { spec_id: 'mage-fire', priority: 'low' }])).rejects.toThrow();
  });

  it('explains refusals', () => {
    expect(needsError(new ApiError(403, ''))).toMatch(/officers/);
    expect(needsError(new ApiError(401, ''))).toMatch(/Sign in/);
    expect(needsError(new ApiError(422, 'No spec has the id x'))).toBe('No spec has the id x');
    expect(needsError(new Error('x'))).toBe('Something went wrong; try again.');
  });
});
