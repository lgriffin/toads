/**
 * Which pages the static preview's pretend sign-in opens. The real site asks the API; the preview has no API, so the
 * layout uses this to show the same public front door, member pages and officer console a visitor would meet.
 */
import { MEMBER_NAV } from '$lib/nav';

export type PreviewRole = 'member' | 'officer' | 'admin';

/** The officer view is Wednesday's raid leader; the super admin view is also a global officer. */
export function hasOfficerPowers(role: PreviewRole | null): boolean {
  return role === 'officer' || role === 'admin';
}
export type Gate = 'open' | 'sign-in' | 'officers-only';

/** The member pages (the Members nav); everything else, including unknown paths and their 404, stays open. */
const MEMBER = MEMBER_NAV.map((i) => i.href);

function under(path: string, prefix: string): boolean {
  return path === prefix || path.startsWith(`${prefix}/`);
}

/** `path` is relative to the base path. */
export function previewGate(path: string, role: PreviewRole | null): Gate {
  const p = path.length > 1 && path.endsWith('/') ? path.slice(0, -1) : path || '/';
  if (!MEMBER.some((prefix) => under(p, prefix))) return 'open';
  if (role === null) return 'sign-in';
  if (under(p, '/officers') && !hasOfficerPowers(role)) return 'officers-only';
  return 'open';
}

export function parseRole(value: string | null): PreviewRole | null {
  return value === 'member' || value === 'officer' || value === 'admin' ? value : null;
}
