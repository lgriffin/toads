import { describe, expect, it } from 'vitest';
import { MEMBER_NAV, PUBLIC_NAV, isActive, memberNav } from './nav';

describe('isActive', () => {
  it('matches the story page only at root', () => {
    expect(isActive('/', '/')).toBe(true);
    expect(isActive('/me', '/')).toBe(false);
    expect(isActive('/hub/', '/')).toBe(false);
  });
  it('matches nested routes and trailing slashes', () => {
    expect(isActive('/raids/abc', '/raids')).toBe(true);
    expect(isActive('/raids/', '/raids')).toBe(true);
    expect(isActive('/raidsx', '/raids')).toBe(false);
    expect(isActive('/hub/', '/hub')).toBe(true);
  });
});

describe('nav groups', () => {
  it('splits public story pages from member pages', () => {
    expect(PUBLIC_NAV.map((i) => i.href)).toEqual(['/', '/recruit', '/highlights']);
    expect(MEMBER_NAV.map((i) => i.href)).toEqual(['/hub', '/raids', '/bank', '/me', '/officers']);
  });
  it('shows Officers to officers only', () => {
    expect(memberNav(false).some((i) => i.href === '/officers')).toBe(false);
    expect(memberNav(true).some((i) => i.href === '/officers')).toBe(true);
  });
});
