import { describe, expect, it } from 'vitest';
import { badgeLabel, earned, progressPercent, qualityColour, qualityTextColour, stacksLabel, type Badge } from './badges';

const badge = (over: Partial<Badge> = {}): Badge => ({
  id: 'attendance',
  name: 'Loyal Toad',
  description: 'Raids attended',
  icon: 'attendance',
  glyph: '🐸',
  tier: 3,
  quality: 'epic',
  tier_name: 'Epic',
  value: 42,
  display: '42 raids',
  stacks: 8,
  next_at: 100,
  next_tier: 'Legendary',
  progress: 0.03,
  ...over
});

describe('badges', () => {
  it('colours tiers by item quality and leaves unearned ones plain', () => {
    expect(qualityColour('epic')).toBe('#a335ee');
    expect(qualityColour('')).toBeNull();
    expect(qualityTextColour('rare')).toBe('#5aa9ff');
  });
  it('keeps only earned badges', () => {
    expect(earned([badge(), badge({ id: 'drums', tier: 0, quality: '' })]).map((b) => b.id)).toEqual(['attendance']);
  });
  it('shows stacks only past the first', () => {
    expect(stacksLabel({ stacks: 20 })).toBe('x20');
    expect(stacksLabel({ stacks: 1 })).toBe('');
  });
  it('says what the badge is and what comes next', () => {
    expect(badgeLabel(badge())).toBe('Loyal Toad, Epic: 42 raids. Legendary at 100.');
    expect(badgeLabel(badge({ tier: 4, quality: 'legendary', tier_name: 'Legendary', next_at: null, next_tier: '' }))).toBe(
      'Loyal Toad, Legendary: 42 raids. Top tier.'
    );
    expect(badgeLabel(badge({ tier: 0, quality: '', tier_name: '', display: '3 raids', next_at: 5, next_tier: 'Uncommon' }))).toBe(
      'Loyal Toad, not earned yet: 3 raids. Uncommon at 5.'
    );
  });
  it('clamps progress', () => {
    expect(progressPercent({ progress: 0.248 })).toBe(25);
    expect(progressPercent({ progress: 2 })).toBe(100);
    expect(progressPercent({ progress: -1 })).toBe(0);
  });
});
