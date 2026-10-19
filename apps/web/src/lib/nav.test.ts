import { describe, expect, it } from 'vitest';
import { MEMBER_NAV, PUBLIC_NAV, isActive, memberNav } from './nav';

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
      '/calendar',
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
