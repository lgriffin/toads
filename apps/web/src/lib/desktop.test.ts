import { existsSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { DESKTOP_CONTRACT, desktopSite, parseDesktopSite } from './desktop';
import { NAV, type NavItem } from './nav';

const routes = new URL('../routes/', import.meta.url);
const isPage = (dir: URL) => ['+page.svelte', '+page.ts'].some((f) => existsSync(new URL(f, dir)));

describe('the desktop app contract (/desktop.json)', () => {
  it('serves every top bar list and the launch hold', () => {
    const site = desktopSite(false);
    expect(site).toEqual({ contract: DESKTOP_CONTRACT, launch_hold: false, nav: NAV });
    expect(parseDesktopSite(JSON.parse(JSON.stringify(site)))).toEqual(site);
    expect(parseDesktopSite(JSON.parse(JSON.stringify(desktopSite(true))))?.launch_hold).toBe(true);
  });

  it('refuses another contract, a missing list and anything but a hub path', () => {
    const site = JSON.parse(JSON.stringify(desktopSite(true)));
    expect(parseDesktopSite(null)).toBeNull();
    expect(parseDesktopSite('<html>')).toBeNull();
    expect(parseDesktopSite({ ...site, contract: DESKTOP_CONTRACT + 1 })).toBeNull();
    expect(parseDesktopSite({ ...site, launch_hold: 'yes' })).toBeNull();
    expect(parseDesktopSite({ ...site, nav: { ...site.nav, officerMenu: undefined } })).toBeNull();
    for (const href of ['https://evil.example/', '//evil.example/x', 'javascript:alert(1)', '/a?b', '/a b', '']) {
      const bad = { ...site, nav: { ...site.nav, hubMenu: [{ href, label: 'Bad' }] } };
      expect(parseDesktopSite(bad), href).toBeNull();
    }
    expect(parseDesktopSite({ ...site, nav: { ...site.nav, hubMenu: [{ href: '/x', label: ' ' }] } })).toBeNull();
  });

  it('keeps only the fields a nav item has', () => {
    const site = JSON.parse(JSON.stringify(desktopSite(true)));
    site.nav.hubMenu = [{ href: '/hub', label: 'Hub', hint: 'h', officerOnly: 'yes', extra: 1 }];
    expect(parseDesktopSite(site)?.nav.hubMenu).toEqual([{ href: '/hub', label: 'Hub', hint: 'h' }]);
  });
});

describe('every top bar link', () => {
  const items: NavItem[] = Object.values(NAV).flat();

  it.each(items.map((i) => [i.href, i.label]))('%s (%s) is a page on the site', (href) => {
    expect(isPage(new URL(href === '/' ? './' : `.${href}/`, routes)), href).toBe(true);
  });

  it("has a page for each raid night's officers", () => {
    expect(isPage(new URL('./officers/nights/[day]/', routes))).toBe(true);
  });
});
