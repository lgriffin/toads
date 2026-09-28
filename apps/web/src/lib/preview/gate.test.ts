import { describe, expect, it } from 'vitest';
import { parseRole, previewGate } from './gate';

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
  });
  it('leaves unknown paths open so they reach the 404 page', () => {
    expect(previewGate('/does-not-exist/', null)).toBe('open');
    expect(previewGate('/hubbub/', null)).toBe('open');
  });
});

describe('parseRole', () => {
  it('accepts only the two roles', () => {
    expect(parseRole('member')).toBe('member');
    expect(parseRole('officer')).toBe('officer');
    expect(parseRole('admin')).toBeNull();
    expect(parseRole(null)).toBeNull();
  });
});
