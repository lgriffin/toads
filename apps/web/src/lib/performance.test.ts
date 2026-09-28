import { describe, expect, it } from 'vitest';
import { metricValue, rankLabel, rolePlural, signed, vsMedian } from './performance';

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
