import { describe, expect, it } from 'vitest';
import { isActive } from './nav';

describe('isActive', () => {
  it('matches home only at root', () => {
    expect(isActive('/', '/')).toBe(true);
    expect(isActive('/me', '/')).toBe(false);
  });
  it('matches nested routes', () => {
    expect(isActive('/raids/abc', '/raids')).toBe(true);
    expect(isActive('/raidsx', '/raids')).toBe(false);
  });
});
