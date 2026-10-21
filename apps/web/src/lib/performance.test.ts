import { describe, expect, it } from 'vitest';
import { metricValue, rankLabel, rolePlural, signed, verdict, vsMedian, type PerformanceEntry, type PerformanceRole } from './performance';

describe('performance', () => {
  it('formats amounts compactly and percentages as they are', () => {
    expect(metricValue(1_234_567, 'amount')).toBe('1.2M');
    expect(metricValue(4_500, 'amount')).toBe('4.5K');
    expect(metricValue(950, 'amount')).toBe('950');
    expect(metricValue(62.54, 'percent')).toBe('62.5%');
  });
  it('compares against the median', () => {
    expect(vsMedian(900, 700)).toBe(29);
    expect(vsMedian(600, 700)).toBe(-14);
    expect(vsMedian(5, 0)).toBe(0);
    expect(signed(29)).toBe('+29%');
    expect(signed(-14)).toBe('-14%');
    expect(signed(0)).toBe('0%');
  });
  it('ranks in plain English', () => {
    expect(rankLabel(1, 6)).toBe('1st of 6');
    expect(rankLabel(2, 6)).toBe('2nd of 6');
    expect(rankLabel(3, 6)).toBe('3rd of 6');
    expect(rankLabel(11, 25)).toBe('11th of 25');
    expect(rankLabel(22, 25)).toBe('22nd of 25');
  });
  it('names the role group', () => {
    expect(rolePlural('healer')).toBe('healers');
    expect(rolePlural('melee')).toBe('melee');
  });
});

describe('the hub home verdict', () => {
  const entry = (value: number, median: number, role: PerformanceRole = 'melee'): PerformanceEntry => ({
    name: 'Hopscotch',
    class: 'Rogue',
    role,
    metric: 'Damage',
    unit: 'amount',
    value,
    median,
    rank: 3,
    of: 9,
    recent: []
  });

  it('says in words how the raid went against the role median', () => {
    expect(verdict(entry(114, 100))).toBe('beat the melee median by 14%');
    expect(verdict(entry(94, 100, 'healer'))).toBe("was 6% under the healers' median");
    expect(verdict(entry(100, 100))).toBe('matched the melee median');
  });
});
