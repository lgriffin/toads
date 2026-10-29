/**
 * The raid leader desk (GET /api/desk, REQ-HUB-DESK-001): what is waiting on this officer for the nights they run.
 * The app counts it on the dock or taskbar and raises one native notification when something new arrives, so an officer
 * with the app in the tray hears about a new application without keeping the hub open. The lines are the hub's own
 * (deskLines in apps/web/src/lib/community-api.ts), so the tray reads like the desk on /hub.
 */
import { deskLines, type DeskSummary } from '../../web/src/lib/community-api';

export type Desk = DeskSummary;

const KEYS: readonly (keyof Desk)[] = [
  'applications_waiting',
  'posts_to_curate',
  'highlights_to_review',
  'spotlights_awaiting_consent'
];

export function parseDesk(body: unknown): Desk | null {
  if (!body || typeof body !== 'object') return null;
  const desk = body as Record<string, unknown>;
  if (!KEYS.every((key) => Number.isInteger(desk[key]) && (desk[key] as number) >= 0)) return null;
  return Object.fromEntries(KEYS.map((key) => [key, desk[key]])) as unknown as Desk;
}

/** Everything waiting: the number on the badge. */
export function waiting(desk: Desk | null): number {
  return desk ? KEYS.reduce((sum, key) => sum + desk[key], 0) : 0;
}

/** The desk's non-empty lines, as the hub words them, for the tray's tooltip and menu. */
export function trayLines(desk: Desk | null): string[] {
  return desk ? deskLines(desk).filter((l) => l.count > 0).map((l) => `${l.label}: ${l.count}`) : [];
}

/**
 * The notification body for what grew since the last look, or null when nothing did. The first look (`before` null)
 * never notifies: an officer opening the app sees the badge, not a burst of alerts for work they already knew about.
 */
export function newWork(before: Desk | null, after: Desk | null): string | null {
  if (!before || !after) return null;
  const was = deskLines(before);
  const grew = deskLines(after)
    .map((line, i) => ({ ...line, added: line.count - was[i].count }))
    .filter((l) => l.added > 0)
    .map((l) => `${l.label}: ${l.count} (${l.added} new)`);
  return grew.length ? grew.join('\n') : null;
}

/**
 * The tray's desk section for an officer, under the hub's heading for it: what waits, or that nothing does. Empty when
 * there is no desk to show (a raider, a visitor, or the hub out of reach), so the tray never claims a clear desk it
 * could not read.
 */
export function trayDesk(desk: Desk | null): string[] {
  if (!desk) return [];
  const lines = trayLines(desk);
  return ['Raid leader desk', ...(lines.length ? lines : ['Nothing waiting'])];
}

/** The Windows taskbar overlay for a count: badge-1 to badge-9, then badge-9plus; null for none. */
export function badgeIcon(count: number): string | null {
  if (count <= 0) return null;
  return count > 9 ? 'badge-9plus.png' : `badge-${count}.png`;
}
