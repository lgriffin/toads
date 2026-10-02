import { describe, expect, it } from 'vitest';
import { ANALYZER_RELEASES, WELCOME_STEPS, isOutside } from './welcome';

describe('welcome checklist', () => {
  it('has unique steps that link inside the hub or to https', () => {
    const ids = WELCOME_STEPS.map((s) => s.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const s of WELCOME_STEPS) expect(s.href.startsWith('/') || isOutside(s.href), s.id).toBe(true);
  });

  it('starts with claiming characters and links the analyzer download', () => {
    expect(WELCOME_STEPS[0].href).toBe('/me/claim');
    expect(WELCOME_STEPS.some((s) => s.href === ANALYZER_RELEASES)).toBe(true);
    expect(isOutside('/bank')).toBe(false);
  });
});
