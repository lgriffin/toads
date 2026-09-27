export interface NavItem {
  href: string;
  label: string;
  /** Shown only to officers; the API is still the gate. */
  officerOnly?: boolean;
}

/** The outward story: public, no login. */
export const PUBLIC_NAV: readonly NavItem[] = [
  { href: '/', label: 'Story' },
  { href: '/recruit', label: 'Recruit' },
  { href: '/highlights', label: 'Highlights' }
];

/** The inward hub for signed-in members. */
export const MEMBER_NAV: readonly NavItem[] = [
  { href: '/hub', label: 'Hub' },
  { href: '/raids', label: 'Raids & Logs' },
  { href: '/bank', label: 'Bank' },
  { href: '/me', label: 'Me' },
  { href: '/officers', label: 'Officers', officerOnly: true }
];

export function memberNav(officer: boolean): NavItem[] {
  return MEMBER_NAV.filter((i) => officer || !i.officerOnly);
}

export function isActive(pathname: string, href: string): boolean {
  const path = pathname.length > 1 && pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
  return href === '/' ? path === '/' : path === href || path.startsWith(`${href}/`);
}
