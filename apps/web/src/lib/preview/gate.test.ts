import { describe, expect, it } from 'vitest';
import { hasOfficerPowers, parseRole, previewGate } from './gate';

describe('previewGate', () => {
  it('keeps the public face open to everyone', () => {
    for (const path of ['/', '', '/story/', '/recruit', '/login/', '/members-only/']) {
      expect(previewGate(path, null)).toBe('open');
    }
  });
  it('asks a signed-out visitor to sign in for member pages', () => {
    for (const path of ['/hub/', '/raids/ssc-0924/', '/me/settings/', '/officers/']) {
      expect(previewGate(path, null)).toBe('sign-in');
    }
  });
  it('opens member pages to both roles and the officer console to officers only', () => {
    expect(previewGate('/hub/', 'member')).toBe('open');
    expect(previewGate('/me/', 'member')).toBe('open');
    expect(previewGate('/officers/', 'member')).toBe('officers-only');
    expect(previewGate('/officers/reference/', 'member')).toBe('officers-only');
    expect(previewGate('/officers/reference/', 'officer')).toBe('open');
    expect(previewGate('/officers/', 'admin')).toBe('open');
  });
  it('gives officer powers to the officer and super admin views', () => {
    expect(hasOfficerPowers('officer')).toBe(true);
    expect(hasOfficerPowers('admin')).toBe(true);
    expect(hasOfficerPowers('member')).toBe(false);
    expect(hasOfficerPowers(null)).toBe(false);
  });
  it('leaves unknown paths open so they reach the 404 page', () => {
    expect(previewGate('/does-not-exist/', null)).toBe('open');
    expect(previewGate('/hubbub/', null)).toBe('open');
  });
});

describe('parseRole', () => {
  it('accepts only the three views', () => {
    expect(parseRole('member')).toBe('member');
    expect(parseRole('officer')).toBe('officer');
    expect(parseRole('admin')).toBe('admin');
    expect(parseRole('root')).toBeNull();
    expect(parseRole(null)).toBeNull();
  });
});
