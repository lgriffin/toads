import { describe, expect, it } from 'vitest';
import { classToad, isArchtoad, memberToads, rankToad, roleToad, toadSrc } from './toads';

describe('toads', () => {
  it('maps a class name to its toad, ignoring case', () => {
    expect(classToad('Priest')).toEqual({ kind: 'class', id: 'classes/priest', label: 'Priest' });
    expect(classToad(' warlock ')?.id).toBe('classes/warlock');
  });

  it('has no toad for an unknown or missing class', () => {
    expect(classToad('Death Knight')).toBeNull();
    expect(classToad(null)).toBeNull();
  });

  it('gives both damage roles the damage toad', () => {
    expect(roleToad('Melee')?.id).toBe('roles/damage');
    expect(roleToad('Ranged')?.id).toBe('roles/damage');
    expect(roleToad('Tank')?.id).toBe('roles/tank');
    expect(roleToad('Healer')?.id).toBe('roles/healer');
  });

  it('gives only officers and super admins a rank toad', () => {
    expect(rankToad('visitor')).toBeNull();
    expect(rankToad('raider')?.id).toBe('ranks/member');
    expect(rankToad('officer')?.id).toBe('ranks/officer');
    expect(rankToad('admin')?.id).toBe('ranks/officer');
  });

  it('gives the Archtoad to _gallagher and nobody else', () => {
    expect(isArchtoad('_gallagher')).toBe(true);
    expect(isArchtoad(' @_Gallagher ')).toBe(true);
    expect(isArchtoad('gallagher')).toBe(false);
    expect(isArchtoad('Hopscotch')).toBe(false);
    expect(isArchtoad(null)).toBe(false);
    expect(rankToad('raider', '_gallagher')?.id).toBe('ranks/archtoad');
    expect(rankToad('admin', 'Hopscotch')?.id).toBe('ranks/officer');
  });

  it('adds the banker and developer toads after the rank', () => {
    const ids = memberToads({ tier: 'officer', titles: ['banker', 'developer'], className: 'Mage' }).map((t) => t.id);
    expect(ids).toEqual(['ranks/officer', 'ranks/banker', 'ranks/developer', 'classes/mage']);
  });

  it('lists an officer healer priest as Officer, Priest, Healer', () => {
    const labels = memberToads({ tier: 'officer', className: 'Priest', role: 'Healer' }).map((t) => t.label);
    expect(labels).toEqual(['Officer', 'Priest', 'Healer']);
  });

  it('leaves out what is not known', () => {
    expect(memberToads({ tier: 'visitor' })).toEqual([]);
    expect(memberToads({ tier: 'raider' }).map((t) => t.label)).toEqual(['Member']);
    expect(memberToads({ tier: 'raider', className: 'Mage' }).map((t) => t.label)).toEqual(['Member', 'Mage']);
  });

  it('builds the artwork path for the standalone toad and the badge', () => {
    expect(toadSrc('/toads', { id: 'classes/mage' })).toBe('/toads/logos/classes/mage.svg');
    expect(toadSrc('', { id: 'ranks/officer' }, true)).toBe('/logos/ranks/officer-badge.svg');
  });
});
