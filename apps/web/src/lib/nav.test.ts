import { describe, expect, it } from 'vitest';
import { HUB_MENU, MEMBER_NAV, OFFICER_MENU, PUBLIC_NAV, currentIn, hubMenu, inMenu, isActive, memberNav, officerMenu } from './nav';

describe('isActive', () => {
  it('matches the landing page only at root', () => {
    expect(isActive('/', '/')).toBe(true);
    expect(isActive('/me', '/')).toBe(false);
    expect(isActive('/hub/', '/')).toBe(false);
  });
  it('matches nested routes and trailing slashes', () => {
    expect(isActive('/logs/abc', '/logs')).toBe(true);
    expect(isActive('/logs/', '/logs')).toBe(true);
    expect(isActive('/logsx', '/logs')).toBe(false);
    expect(isActive('/raids', '/raid')).toBe(false);
    expect(isActive('/hub/', '/hub')).toBe(true);
  });
});

describe('nav groups', () => {
  it('splits public pages from member pages', () => {
    expect(PUBLIC_NAV.map((i) => i.href)).toEqual(['/', '/how-we-raid', '/features', '/story', '/recruit']);
    expect(MEMBER_NAV.map((i) => i.href)).toEqual([
      '/hub',
      '/raid',
      '/logs',
      '/highlights',
      '/bank',
      '/me',
      '/officers',
      '/admin'
    ]);
  });
  it('shows Officers to officers only', () => {
    expect(memberNav(false).some((i) => i.href === '/officers')).toBe(false);
    expect(memberNav(true).some((i) => i.href === '/officers')).toBe(true);
  });
  it('shows Admin to super admins only', () => {
    expect(memberNav(true).some((i) => i.href === '/admin')).toBe(false);
    expect(memberNav(false, true).map((i) => i.href)).toContain('/officers');
    expect(memberNav(true, true).some((i) => i.href === '/admin')).toBe(true);
  });
});

describe('top bar menus', () => {
  const hrefs = (groups: { items: { href: string }[] }[]) => groups.flatMap((g) => g.items.map((i) => i.href));

  it('puts Raid and Logs under Hub, then the public pages, and leaves Me and officer pages out of it', () => {
    const groups = hubMenu(memberNav(true, true));
    expect(groups.map((g) => g.label)).toEqual(['Your hub', 'About the guild']);
    expect(hrefs([groups[0]])).toEqual(['/hub', '/raid', '/logs', '/highlights', '/bank']);
    expect(hrefs([groups[1]])).toEqual(PUBLIC_NAV.map((i) => i.href));
    expect(hrefs(groups)).not.toContain('/me');
    expect(hrefs(groups).some((h) => h.startsWith('/officers') || h === '/admin')).toBe(false);
  });

  it('keeps out of the Hub menu any page the member cannot open', () => {
    const held = memberNav(false).filter((i) => ['/hub', '/raid', '/me'].includes(i.href));
    expect(hrefs([hubMenu(held)[0]])).toEqual(['/hub', '/raid']);
  });

  it('gives raiders no Officers menu', () => {
    expect(officerMenu(false, false, [{ day: 'wed', name: 'Wednesday' }])).toEqual([]);
  });

  it('lists only the raid nights an officer runs', () => {
    const groups = officerMenu(true, false, [{ day: 'sun', name: 'Sunday' }]);
    expect(groups.map((g) => g.label)).toEqual(['Officer tools', 'Your raid night']);
    expect(hrefs(groups)).toContain('/officers/nights/sun');
    expect(hrefs(groups)).not.toContain('/officers/nights/wed');
    expect(hrefs(groups)).not.toContain('/admin');
  });

  it('adds the Admin console for super admins only', () => {
    const nights = ['wed', 'thu', 'sun'].map((day) => ({ day, name: day }));
    const groups = officerMenu(true, true, nights);
    expect(groups.map((g) => g.label)).toEqual(['Officer tools', 'Your raid nights', 'Super admin']);
    expect(hrefs(groups).at(-1)).toBe('/admin');
  });

  it('marks the menu and the one link for the current page', () => {
    const groups = officerMenu(true, false, [{ day: 'wed', name: 'Wednesday' }]);
    expect(inMenu('/officers/calendar/', groups)).toBe(true);
    expect(currentIn('/officers/calendar/', groups)).toBe('/officers/calendar');
    expect(currentIn('/officers/nights/wed/', groups)).toBe('/officers/nights/wed');
    expect(currentIn('/officers/', groups)).toBe('/officers');
    expect(inMenu('/me', groups)).toBe(false);
  });

  it('gives every Hub and officer tool a plain one-line hint', () => {
    for (const item of [...HUB_MENU, ...OFFICER_MENU]) expect(item.hint?.length).toBeGreaterThan(0);
  });
});
