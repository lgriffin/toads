import { describe, expect, it } from 'vitest';
import { memberNav } from './nav';
import { TAB_PREVIEW, TAB_PURPOSE, UPCOMING, absencesOnly, heldNav, isMemberPath, launchHold, tabOf } from './launch';

describe('launch hold', () => {
  it('gives raiders the coming-soon page on every member page', () => {
    for (const path of ['/hub', '/logs/42', '/bank/', '/me/claim', '/welcome', '/highlights'])
      expect(launchHold(path, 'raider', true)).toBe('coming-soon');
  });

  it('opens the Raid page and Me, where absences live, to every signed-in tier', () => {
    for (const tier of ['raider', 'officer', 'admin'] as const)
      for (const path of ['/raid', '/raid/', '/me', '/me/']) expect(launchHold(path, tier, true)).toBe('open');
    // The old /raids and /calendar links only redirect.
    for (const path of ['/raids', '/calendar']) expect(launchHold(path, 'raider', true)).toBe('open');
  });

  it('keeps a raider\'s Me to their absences while the hold is on', () => {
    expect(absencesOnly('raider', true)).toBe(true);
    for (const tier of ['officer', 'admin'] as const) expect(absencesOnly(tier, true)).toBe(false);
    expect(absencesOnly('raider', false)).toBe(false);
  });

  it('opens every page to officers but the bank, which keeps the Forever notice', () => {
    for (const item of memberNav(true).filter((i) => i.href !== '/bank')) expect(launchHold(item.href, 'officer', true)).toBe('open');
    for (const path of ['/logs/42', '/me/claim', '/me/settings', '/officers/reference', '/welcome'])
      expect(launchHold(path, 'officer', true)).toBe('open');
    for (const path of ['/bank', '/bank/']) expect(launchHold(path, 'officer', true)).toBe('forever-notice');
    expect(launchHold('/officers', 'raider', true)).toBe('coming-soon');
  });

  it('gives super admins exactly the officers\' view, with the Admin console open', () => {
    for (const path of ['/hub', '/logs', '/raid', '/highlights', '/bank', '/me', '/me/claim', '/officers/calendar', '/welcome'])
      expect(launchHold(path, 'admin', true)).toBe(launchHold(path, 'officer', true));
    expect(launchHold('/me', 'admin', true)).toBe('open');
    expect(launchHold('/bank', 'admin', true)).toBe('forever-notice');
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

  it('shows raiders the hub, Raid and Me links and leaves other tiers their tabs', () => {
    expect(heldNav(memberNav(false), 'raider', true).map((i) => i.href)).toEqual(['/hub', '/raid', '/me']);
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

  it('previews the bank tab with its intent, coming features and mockup', () => {
    expect(Object.keys(TAB_PREVIEW)).toEqual(['/bank']);
    const bank = TAB_PREVIEW['/bank'];
    expect(bank.intent).toBeTruthy();
    expect(bank.sections.flatMap((s) => s.items).length).toBeGreaterThanOrEqual(4);
    expect(bank.mockup).toBe('bank');
    expect(bank.sections.map((s) => s.title)).toContain('For bankers, and visible to officers');
  });
});
