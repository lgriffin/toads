/**
 * The homepage's guild pulse: a few guild-level facts that show the guild is active, worked out from the raid sheet
 * trend (`/api/raid-sheets/trend`, newest first). Guild totals only; nothing here names a player.
 */
import type { ZoneProgress } from './community';
import type { NextRaid } from './next-raid';
import type { RaidHeadline } from './sheets';

export interface GuildPulse {
  next: NextRaid | null;
  now: Date;
  progression: ZoneProgress[];
  /** Newest first, as the API returns it. */
  trend: RaidHeadline[];
}

export interface Point {
  date: string;
  value: number;
}

/** One zone's clear times, oldest first, skipping raids that did not clear it. */
export function clearTrend(trend: readonly RaidHeadline[], zone: string): Point[] {
  const points: Point[] = [];
  for (const raid of trend) {
    const clear = raid.clear_times.find((c) => c.zone === zone);
    if (clear && clear.seconds > 0) points.push({ date: raid.raid_date, value: clear.seconds });
  }
  return points.sort((a, b) => a.date.localeCompare(b.date));
}

/** The newest timed raid's first timed zone, as its sheet title lists it (the night's main raid). */
export function mainZone(trend: readonly RaidHeadline[]): string | null {
  for (const raid of trend) {
    const clear = raid.clear_times.find((c) => c.seconds > 0);
    if (clear) return clear.zone;
  }
  return null;
}

export interface Fastest {
  zone: string;
  seconds: number;
  date: string;
  /** Seconds saved against the oldest clear in the trend; 0 when the oldest is also the fastest. */
  saved: number;
  /** How many timed clears of the zone the trend holds. */
  clears: number;
  /** The date of that oldest clear. */
  since: string;
}

export function fastestClear(trend: readonly RaidHeadline[], zone: string | null = mainZone(trend)): Fastest | null {
  if (!zone) return null;
  const points = clearTrend(trend, zone);
  if (!points.length) return null;
  const best = points.reduce((a, b) => (b.value < a.value ? b : a));
  return {
    zone,
    seconds: best.value,
    date: best.date,
    saved: Math.max(0, points[0].value - best.value),
    clears: points.length,
    since: points[0].date
  };
}

/** A field of the trend, oldest first, skipping raids where the sheet had no value. */
export function series(
  trend: readonly RaidHeadline[],
  pick: (raid: RaidHeadline) => number | null | undefined,
  limit = 4
): Point[] {
  const points: Point[] = [];
  for (const raid of trend) {
    const value = pick(raid);
    if (value !== null && value !== undefined && Number.isFinite(value)) points.push({ date: raid.raid_date, value });
  }
  return points.slice(0, limit).sort((a, b) => a.date.localeCompare(b.date));
}

/** Bosses killed and in total across every zone. */
export function totalProgress(zones: readonly ZoneProgress[]): { killed: number; total: number } {
  return zones.reduce((t, z) => ({ killed: t.killed + z.killed, total: t.total + z.total }), { killed: 0, total: 0 });
}

/** "15 minutes" or "1 minute"; under a minute reads as "under a minute". */
export function minutes(seconds: number): string {
  if (seconds < 60) return 'under a minute';
  const m = Math.round(seconds / 60);
  return m === 1 ? '1 minute' : `${m} minutes`;
}
