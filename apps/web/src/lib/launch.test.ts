import { describe, expect, it } from 'vitest';
import { memberNav } from './nav';
import { TAB_PURPOSE, UPCOMING, heldNav, isMemberPath, launchHold, tabOf } from './launch';

describe('launch hold', () => {
  it('gives raiders the coming-soon page on every member page', () => {
    for (const path of ['/hub', '/raids/42', '/bank/', '/me/claim', '/welcome', '/highlights'])
      expect(launchHold(path, 'raider', true)).toBe('coming-soon');
  });

  it('gives officers the Forever launch notice on every tab, their console included', () => {
    for (const item of memberNav(true)) expect(launchHold(item.href, 'officer', true)).toBe('forever-notice');
  });

  it('leaves super admins, visitors and the public pages alone', () => {
    expect(launchHold('/officers', 'admin', true)).toBe('open');
    // An officer who opens the admin console meets its own super-admins-only refusal, not the notice.
    expect(launchHold('/admin', 'officer', true)).toBe('open');
    expect(launchHold('/hub', 'visitor', true)).toBe('open');
    for (const path of ['/', '/how-we-raid', '/story', '/recruit', '/toolkit', '/members-only', '/hubbub'])
      expect(launchHold(path, 'raider', true)).toBe('open');
  });

  it('opens everything once the hold is lifted', () => {
    expect(launchHold('/hub', 'raider', false)).toBe('open');
    expect(launchHold('/officers', 'officer', false)).toBe('open');
  });

  it('shows raiders a single member link and leaves other tiers their tabs', () => {
    expect(heldNav(memberNav(false), 'raider', true).map((i) => i.href)).toEqual(['/hub']);
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
});
