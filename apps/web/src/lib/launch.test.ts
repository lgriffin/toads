import { describe, expect, it } from 'vitest';
import { memberNav } from './nav';
import { TAB_PREVIEW, TAB_PURPOSE, UPCOMING, isHeldPublic, publicNav, heldNav, isMemberPath, launchHold, tabOf } from './launch';

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
    for (const path of ['/', '/how-we-raid', '/story', '/recruit', '/features', '/toolkit', '/members-only', '/hubbub'])
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

  it('previews the officers, bank, highlights and me tabs with their intent and coming features', () => {
    expect(Object.keys(TAB_PREVIEW).sort()).toEqual(['/bank', '/highlights', '/me', '/officers']);
    for (const p of Object.values(TAB_PREVIEW)) {
      expect(p.intent).toBeTruthy();
      expect(p.sections.flatMap((s) => s.items).length).toBeGreaterThanOrEqual(4);
    }
    const officers = TAB_PREVIEW['/officers'].sections.flatMap((s) => s.items).join(' ');
    for (const word of ['strateg', 'ttendance', 'adge', 'Warcraft Logs']) expect(officers).toContain(word);
    expect(TAB_PREVIEW['/bank'].mockup).toBe('bank');
    expect(TAB_PREVIEW['/bank'].sections.map((s) => s.title)).toContain('For bankers, and visible to officers');
    expect(TAB_PREVIEW['/me'].sections[0].items.join(' ')).toContain('alts');
  });

  it('trims the public site to our story until the launch, for every visitor', () => {
    expect(publicNav(true)).toEqual([{ href: '/', label: 'Our story' }]);
    expect(publicNav(false).map((i) => i.href)).toEqual(['/', '/how-we-raid', '/features', '/story', '/recruit']);
    for (const path of ['/how-we-raid', '/features/', '/toolkit', '/story', '/recruit/'])
      expect(isHeldPublic(path, true)).toBe(true);
    for (const path of ['/', '/hub', '/login', '/members-only', '/storyteller']) expect(isHeldPublic(path, true)).toBe(false);
    expect(isHeldPublic('/recruit', false)).toBe(false);
  });
});
