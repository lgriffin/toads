import { describe, expect, it } from 'vitest';
import { countdown, localStart, signupLink } from './next-raid';

describe('next raid', () => {
  const now = new Date('2026-09-28T10:00:00Z');

  it('counts down in the largest sensible unit', () => {
    expect(countdown('2026-09-28T10:01:00Z', now)).toBe('in 1 minute');
    expect(countdown('2026-09-28T10:45:00Z', now)).toBe('in 45 minutes');
    expect(countdown('2026-09-28T15:00:00Z', now)).toBe('in 5 hours');
    expect(countdown('2026-09-29T11:00:00Z', now)).toBe('tomorrow');
    expect(countdown('2026-10-01T10:00:00Z', now)).toBe('in 3 days');
  });
  it('says when the raid is under way', () => {
    expect(countdown('2026-09-28T09:00:00Z', now)).toBe('Under way');
    expect(countdown('2026-09-28T12:00:00Z', now, true)).toBe('Under way');
  });
  it('shows the start in the viewer’s timezone', () => {
    expect(localStart('2026-09-30T17:30:00Z', 'Europe/Paris')).toContain('19:30');
    expect(localStart('2026-09-30T17:30:00Z', 'Europe/London')).toContain('18:30');
  });
  it('links only Discord event pages', () => {
    expect(signupLink({ url: 'https://discord.com/events/77/4242' })).toBe('https://discord.com/events/77/4242');
    expect(signupLink({ url: 'javascript:alert(1)' })).toBeNull();
    expect(signupLink({ url: 'https://evil.test/events/1/2' })).toBeNull();
    expect(signupLink({ url: null })).toBeNull();
  });
});
