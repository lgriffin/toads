import { describe, expect, it } from 'vitest';
import { AWARDABLE, awardable, monthLabel, titlesOf } from './awards';
import { MILESTONES } from './milestones';
import { previewAwards, previewAwardsOf } from './preview/awards-fake';

describe('awards', () => {
  it('can give every milestone and achievement, and the three titles', () => {
    expect(AWARDABLE.length).toBe(MILESTONES.length + 3);
    expect(awardable('discord-admin')).toMatchObject({ kind: 'title', file: 'ranks/discord-admin' });
    expect(awardable('raider-of-the-month')).toMatchObject({ kind: 'milestone', monthly: true });
    expect(awardable('level-60')).toMatchObject({ kind: 'achievement', monthly: false });
  });

  it('picks the titles out of a member’s awards, in a fixed order', () => {
    const held = [
      { award_id: 'developer', kind: 'title' as const },
      { award_id: 'level-60', kind: 'achievement' as const },
      { award_id: 'banker', kind: 'title' as const }
    ];
    expect(titlesOf(held)).toEqual(['banker', 'developer']);
  });

  it('names a month', () => {
    expect(monthLabel('2026-09')).toBe('September 2026');
  });

  it('keeps the preview’s awards to the same rules as the hub', async () => {
    const before = previewAwardsOf(2).length;
    await expect(previewAwards.give({ member_id: 2, award_id: 'raider-of-the-month' })).rejects.toMatchObject({
      status: 422
    });
    const given = await previewAwards.give({ member_id: 2, award_id: 'chef' });
    await expect(previewAwards.give({ member_id: 2, award_id: 'chef' })).rejects.toMatchObject({ status: 409 });
    expect(previewAwardsOf(2).length).toBe(before + 1);
    await previewAwards.takeBack(given.id);
    expect(previewAwardsOf(2).length).toBe(before);
  });
});
