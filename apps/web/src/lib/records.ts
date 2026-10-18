/**
 * The guild's fastest full clears, from the Warcraft Logs reports officers uploaded. Site text like landing.ts: it is
 * the best clear time per raid across all of the guild's logs on Fresh Warcraft Logs, with the report each came from.
 * Officers refresh it here, in a PR, when a record falls.
 */

export interface ClearRecord {
  raid: string;
  /** Full-clear time in milliseconds. */
  ms: number;
  /** YYYY-MM-DD of the raid. */
  date: string;
  /** The Warcraft Logs report code. */
  code: string;
}

export interface RecordGroup {
  id: 'fresh' | 'tbc';
  title: string;
  /** What the group is, for the line under its title. */
  blurb: string;
  records: ClearRecord[];
}

export const RECORD_GROUPS: readonly RecordGroup[] = [
  {
    id: 'fresh',
    title: 'Fresh',
    blurb: 'Molten Core to Naxxramas',
    records: [
      { raid: 'Molten Core', ms: 1574262, date: '2025-03-12', code: 'McKHjbrYn9tZ6mkG' },
      { raid: 'Blackwing Lair', ms: 1463316, date: '2025-06-18', code: 'yfqCRWFGBaTLDYd7' },
      { raid: 'Temple of Ahn’Qiraj', ms: 2362707, date: '2025-09-17', code: 'YDC27gyXcnmzv8QB' },
      { raid: 'Naxxramas', ms: 4651737, date: '2025-12-10', code: 'TJ3AMfyj67QFnZxw' }
    ]
  },
  {
    id: 'tbc',
    title: 'The Burning Crusade',
    blurb: 'Serpentshrine Cavern to Black Temple',
    records: [
      { raid: 'Serpentshrine Cavern', ms: 2703387, date: '2026-07-22', code: 'dYvBwCt2yf6XMgxQ' },
      { raid: 'Tempest Keep', ms: 2602336, date: '2026-07-01', code: 'HNb9t4qZ7RXLFdwK' },
      { raid: 'Hyjal Summit', ms: 3494558, date: '2026-09-23', code: 'GgxAzLvYMmD91aK6' },
      { raid: 'Black Temple', ms: 5829689, date: '2026-09-23', code: 'GgxAzLvYMmD91aK6' }
    ]
  }
];

/** 5829689 -> 1:37:10 (hours:minutes:seconds, hours dropped under one). */
export function clearClock(ms: number): string {
  const total = Math.round(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n: number) => String(n).padStart(2, '0');
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

export function reportUrl(code: string): string {
  return `https://fresh.warcraftlogs.com/reports/${code}`;
}
