import { describe, expect, it } from 'vitest';
import { AWARDABLE, awardable, isWeek, isoWeek, monthLabel, periodLabel, titlesOf } from './awards';
import { MILESTONES } from './milestones';
import { previewAwards, previewAwardsOf } from './preview/awards-fake';

describe('awards', () => {
  it('can give every milestone and achievement, and the three titles', () => {
    expect(AWARDABLE.length).toBe(MILESTONES.length + 3);
    expect(awardable('discord-admin')).toMatchObject({ kind: 'title', file: 'ranks/discord-admin' });
    expect(awardable('raider-of-the-month')).toMatchObject({ kind: 'milestone', monthly: true });
    expect(awardable('level-60')).toMatchObject({ kind: 'achievement', monthly: false, weekly: false });
    expect(awardable('sunder-king')).toMatchObject({ kind: 'honour', weekly: true, file: 'honours/sunder-king' });
  });

  it('gives every weekly honour per week, Raider of the Week first', () => {
    const honours = AWARDABLE.filter((a) => a.kind === 'honour');
    expect(honours[0].id).toBe('raider-of-the-week');
    expect(honours.every((a) => a.weekly && !a.monthly)).toBe(true);
    expect(AWARDABLE.filter((a) => a.weekly)).toEqual(honours);
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
    expect(periodLabel('2026-09')).toBe('September 2026');
  });

  it('names a raid week by its Monday, and finds the week a day is in', () => {
    expect(periodLabel('2026-W43')).toBe('week of 19 Oct 2026');
    expect(periodLabel('2026-W01')).toBe('week of 29 Dec 2025');
    expect(isoWeek(new Date(2026, 9, 21))).toBe('2026-W43');
    expect(isoWeek(new Date(2027, 0, 3))).toBe('2026-W53');
    expect(isoWeek(new Date(2025, 11, 29))).toBe('2026-W01');
    expect(['2026-W43', '2026-W53', '2020-W53'].every(isWeek)).toBe(true);
    expect(['2025-W53', '2026-W54', '2026-W00', '2026-10', '2026W43'].some(isWeek)).toBe(false);
  });

  it('keeps the preview’s awards to the same rules as the hub', async () => {
    const before = previewAwardsOf(2).length;
    await expect(previewAwards.give({ member_id: 2, award_id: 'raider-of-the-month' })).rejects.toMatchObject({
      status: 422
    });
    await expect(previewAwards.give({ member_id: 2, award_id: 'pet-pull' })).rejects.toMatchObject({ status: 422 });
    await expect(previewAwards.give({ member_id: 2, award_id: 'pet-pull', period: '2026-W54' })).rejects.toMatchObject({
      status: 422
    });
    const given = await previewAwards.give({ member_id: 2, award_id: 'chef' });
    await expect(previewAwards.give({ member_id: 2, award_id: 'chef' })).rejects.toMatchObject({ status: 409 });
    expect(previewAwardsOf(2).length).toBe(before + 1);
    await previewAwards.takeBack(given.id);
    expect(previewAwardsOf(2).length).toBe(before);
  });
});
