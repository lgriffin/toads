/**
 * GET /api/me/performance (services/api/src/toads_api/home/performance.py): the member's main character in the
 * guild's last analysed raid, against the guild median for the same role.
 */

export type PerformanceRole = 'tank' | 'healer' | 'melee' | 'ranged';

export interface RecentRaid {
  date: string;
  value: number;
  median: number;
}

export interface PerformanceEntry {
  name: string;
  class: string;
  role: PerformanceRole;
  /** The role's primary metric: "Healing", "Damage" or "Mitigation". */
  metric: string;
  unit: 'amount' | 'percent';
  value: number;
  median: number;
  rank: number;
  of: number;
  /** Up to five raids in this role, oldest first, ending with the last raid. */
  recent: RecentRaid[];
}

export interface MyPerformance {
  /** Null until the worker has published. */
  generated_at: string | null;
  raid: { report_id: string; title: string; date: string } | null;
  /** Null when none of the member's characters was in the last raid. */
  entry: PerformanceEntry | null;
  matched_by: 'chosen' | 'claim' | 'nickname' | null;
  /** The characters looked for, best first. */
  looked_for: string[];
}

const ROLE_PLURAL: Record<PerformanceRole, string> = {
  tank: 'tanks',
  healer: 'healers',
  melee: 'melee',
  ranged: 'ranged'
};

export function rolePlural(role: PerformanceRole): string {
  return ROLE_PLURAL[role];
}

/** 12345678 -> "12.3M", 4500 -> "4.5K", 62.5 percent -> "62.5%". */
export function metricValue(value: number, unit: PerformanceEntry['unit']): string {
  if (unit === 'percent') return `${Math.round(value * 10) / 10}%`;
  for (const [size, suffix] of [
    [1e9, 'B'],
    [1e6, 'M'],
    [1e3, 'K']
  ] as const) {
    if (Math.abs(value) >= size) return `${(value / size).toFixed(1)}${suffix}`;
  }
  return String(Math.round(value));
}

/** Whole percent above (+) or below (-) the median; 0 when the median is 0. */
export function vsMedian(value: number, median: number): number {
  return median ? Math.round(((value - median) / median) * 100) : 0;
}

export function signed(n: number): string {
  return n > 0 ? `+${n}%` : `${n}%`;
}

/** "1st of 6", "22nd of 25". */
export function rankLabel(rank: number, of: number): string {
  const tens = rank % 100;
  const suffix = tens >= 11 && tens <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[rank % 10] ?? 'th';
  return `${rank}${suffix} of ${of}`;
}
