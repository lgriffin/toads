/**
 * Which pages the static preview's pretend sign-in opens. The real site asks the API; the preview has no API, so the
 * layout uses this to show the same public front door, member pages and officer console a visitor would meet.
 */
export type PreviewRole = 'member' | 'officer';
export type Gate = 'open' | 'sign-in' | 'officers-only';

/** Pages anyone may see signed out: the public face, the pretend sign-in and the members-only notice. */
const PUBLIC = ['/', '/story', '/recruit', '/login', '/members-only'];

function under(path: string, prefix: string): boolean {
  return prefix === '/' ? path === '/' : path === prefix || path.startsWith(`${prefix}/`);
}

/** `path` is relative to the base path. */
export function previewGate(path: string, role: PreviewRole | null): Gate {
  const p = path.length > 1 && path.endsWith('/') ? path.slice(0, -1) : path || '/';
  if (PUBLIC.some((prefix) => under(p, prefix))) return 'open';
  if (role === null) return 'sign-in';
  if (under(p, '/officers') && role !== 'officer') return 'officers-only';
  return 'open';
}

export function parseRole(value: string | null): PreviewRole | null {
  return value === 'member' || value === 'officer' ? value : null;
}
