/** Top-level screens from the Toads Guild Hub design canvas. */
export const NAV = [
  { href: '/', label: 'Home' },
  { href: '/raids', label: 'Raids & Logs' },
  { href: '/bank', label: 'Bank' },
  { href: '/me', label: 'Me' }
] as const;

export function isActive(pathname: string, href: string): boolean {
  return href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(`${href}/`);
}
