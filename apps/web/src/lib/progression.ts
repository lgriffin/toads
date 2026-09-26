import type { ZoneProgress } from './community';
import type { Raid } from './mock/data';

/** TBC tiers in raid order; zones not listed sort after these, alphabetically. */
export const ZONE_ORDER = [
  'Karazhan',
  "Gruul's Lair",
  "Magtheridon's Lair",
  'Serpentshrine Cavern',
  'Tempest Keep',
  'Mount Hyjal',
  'Black Temple',
  "Zul'Aman",
  'Sunwell Plateau'
];

function rank(zone: string): number {
  const i = ZONE_ORDER.indexOf(zone);
  return i === -1 ? ZONE_ORDER.length : i;
}

/** Aggregate kills per zone across all raids: a boss counts once it has died in any raid. No per-player data. */
export function progressionFromRaids(raids: readonly Raid[]): ZoneProgress[] {
  const zones = new Map<string, { bosses: Set<string>; killed: Set<string> }>();
  for (const raid of raids) {
    const z = zones.get(raid.zone) ?? { bosses: new Set(), killed: new Set() };
    for (const b of raid.bosses) {
      z.bosses.add(b.name);
      if (b.killed) z.killed.add(b.name);
    }
    zones.set(raid.zone, z);
  }
  return [...zones.entries()]
    .map(([zone, z]) => ({ zone, killed: z.killed.size, total: z.bosses.size }))
    .sort((a, b) => rank(a.zone) - rank(b.zone) || a.zone.localeCompare(b.zone));
}
