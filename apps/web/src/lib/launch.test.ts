import { describe, expect, it } from 'vitest';
import { memberNav } from './nav';
import { TAB_PREVIEW, TAB_PURPOSE, UPCOMING, heldNav, isMemberPath, launchHold, tabOf } from './launch';

describe('launch hold', () => {
  it('gives raiders the coming-soon page on every member page', () => {
    for (const path of ['/hub', '/logs/42', '/bank/', '/me/claim', '/welcome', '/highlights'])
      expect(launchHold(path, 'raider', true)).toBe('coming-soon');
  });

  it('opens the Raid page and the Calendar to every signed-in tier', () => {
    for (const tier of ['raider', 'officer', 'admin'] as const)
      for (const path of ['/raid', '/raid/', '/calendar', '/calendar/']) expect(launchHold(path, tier, true)).toBe('open');
    expect(launchHold('/raids', 'raider', true)).toBe('open');
  });

  it('gives officers the Forever launch notice on every tab but their console, which stays open', () => {
    const open = ['/officers', '/raid', '/calendar'];
    for (const item of memberNav(true).filter((i) => !open.includes(i.href)))
      expect(launchHold(item.href, 'officer', true)).toBe('forever-notice');
    for (const path of ['/officers', '/officers/', '/officers/reference']) expect(launchHold(path, 'officer', true)).toBe('open');
    expect(launchHold('/officers', 'raider', true)).toBe('coming-soon');
  });

  it('gives super admins exactly the officers\' view, with the Admin console open', () => {
    for (const path of ['/hub', '/logs', '/raid', '/calendar', '/highlights', '/bank', '/me', '/me/claim', '/welcome'])
      expect(launchHold(path, 'admin', true)).toBe(launchHold(path, 'officer', true));
    expect(launchHold('/me', 'admin', true)).toBe('forever-notice');
    expect(launchHold('/officers', 'admin', true)).toBe('open');
    expect(launchHold('/admin', 'admin', true)).toBe('open');
  });

  it('leaves visitors and the public pages alone', () => {
    // An officer who opens the admin console meets its own super-admins-only refusal, not the notice.
    expect(launchHold('/admin', 'officer', true)).toBe('open');
    expect(launchHold('/hub', 'visitor', true)).toBe('open');
    for (const path of ['/', '/how-we-raid', '/story', '/recruit', '/features', '/toolkit', '/members-only', '/hubbub'])
      expect(launchHold(path, 'raider', true)).toBe('open');
  });

  it('opens everything once the hold is lifted', () => {
    expect(launchHold('/hub', 'raider', false)).toBe('open');
    expect(launchHold('/officers', 'officer', false)).toBe('open');
  });

  it('shows raiders the hub, Raid and Calendar links and leaves other tiers their tabs', () => {
    expect(heldNav(memberNav(false), 'raider', true).map((i) => i.href)).toEqual(['/hub', '/raid', '/calendar']);
    expect(heldNav(memberNav(true), 'officer', true)).toEqual(memberNav(true));
    expect(heldNav(memberNav(false), 'raider', false)).toEqual(memberNav(false));
  });

  it('says what every held tab will hold', () => {
    for (const item of memberNav(true)) {
      expect(isMemberPath(item.href)).toBe(true);
      expect(TAB_PURPOSE[tabOf(`${item.href}/`)!.href]).toBeTruthy();
    }
    expect(isMemberPath('/admin')).toBe(false);
    expect(tabOf('/welcome')?.label).toBe('Welcome');
  });

  it('promises the bank, logs analysis and raid assistance', () => {
    expect(UPCOMING.map((u) => u.title)).toEqual(['Guild bank management', 'Logs analysis', 'Raid assistance']);
  });

  it('previews the bank, highlights and me tabs with their intent and coming features', () => {
    expect(Object.keys(TAB_PREVIEW).sort()).toEqual(['/bank', '/highlights', '/me']);
    for (const p of Object.values(TAB_PREVIEW)) {
      expect(p.intent).toBeTruthy();
      expect(p.sections.flatMap((s) => s.items).length).toBeGreaterThanOrEqual(4);
    }
    expect(TAB_PREVIEW['/bank'].mockup).toBe('bank');
    expect(TAB_PREVIEW['/bank'].sections.map((s) => s.title)).toContain('For bankers, and visible to officers');
    expect(TAB_PREVIEW['/me'].sections[0].items.join(' ')).toContain('alts');
    expect(TAB_PREVIEW['/me'].ownToads).toBe(true);
  });
});
