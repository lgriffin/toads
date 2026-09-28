/**
 * GET /api/home/next-raid (services/api/src/toads_api/home/next_raid.py): the soonest Discord scheduled event, or,
 * while Discord has none coming up, the next raid from the raid days' configured start times.
 */

export interface NextRaid {
  name: string;
  /** ISO 8601, UTC. */
  starts_at: string;
  ends_at: string | null;
  raid_day_id: string | null;
  raid_day_name: string | null;
  /** "discord": an event officers posted; "schedule": the raid day's usual start time. */
  source: 'discord' | 'schedule';
  under_way: boolean;
  /** Members interested in the Discord event; null for a scheduled start. */
  interested: number | null;
  /** The Discord event page, where members sign up. */
  url: string | null;
}

export interface NextRaidAnswer {
  raid: NextRaid | null;
}

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** "Starting now", "in 45 minutes", "in 5 hours", "tomorrow", "in 3 days". */
export function countdown(startsAt: string, now: Date, underWay = false): string {
  const ms = new Date(startsAt).getTime() - now.getTime();
  if (underWay || ms <= 0) return 'Under way';
  if (ms < HOUR) {
    const m = Math.max(1, Math.round(ms / MINUTE));
    return `in ${m} minute${m === 1 ? '' : 's'}`;
  }
  if (ms < DAY) {
    const h = Math.round(ms / HOUR);
    return `in ${h} hour${h === 1 ? '' : 's'}`;
  }
  const d = Math.round(ms / DAY);
  return d === 1 ? 'tomorrow' : `in ${d} days`;
}

/** The start in the viewer's own timezone ("Wednesday 30 Sept, 19:30"); `timeZone` is for tests. */
export function localStart(startsAt: string, timeZone?: string): string {
  return new Date(startsAt).toLocaleString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    ...(timeZone ? { timeZone } : {})
  });
}

/** Only Discord's own event pages are linked: the URL is built by the API, but it is still checked here. */
export function signupLink(raid: Pick<NextRaid, 'url'>): string | null {
  return raid.url && /^https:\/\/discord\.com\/events\/\d+\/\d+$/.test(raid.url) ? raid.url : null;
}
