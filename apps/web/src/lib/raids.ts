import type { Raid } from './mock/data';

export interface RaidFilter {
  zone: string;
  raidDay: string;
  size: string;
  lookbackDays: number;
}

export const ALL = 'all';

/** Zone, raid day, size and lookback, matching the desktop app's filters (REQ-HUB-RAID-002). */
export function filterRaids(raids: Raid[], f: RaidFilter, now: Date): Raid[] {
  const cutoff = now.getTime() - f.lookbackDays * 86_400_000;
  return raids.filter(
    (r) =>
      (f.zone === ALL || r.zone === f.zone) &&
      (f.raidDay === ALL || r.raidDay === f.raidDay) &&
      (f.size === ALL || String(r.size) === f.size) &&
      new Date(r.date).getTime() >= cutoff
  );
}
