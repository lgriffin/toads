import { describe, expect, it } from 'vitest';
import type { Session } from '../../web/src/lib/api';
import { desktopSite } from '../../web/src/lib/desktop';
import { ACCOUNT_MENU, NAV, OFFICER_MENU, SIGN_IN, SIGN_OUT } from '../../web/src/lib/nav';
import { BUNDLED_SITE, menusFor, parseSession, type Menus } from '../src/menus';

const NAMES = { wednesday: 'Wednesday', sunday: 'Sunday' };

function session(over: Partial<Session> = {}): Session {
  return {
    member_id: 1,
    display_name: 'Hopscotch',
    global_officer: false,
    super_admin: false,
    day_roles: { wednesday: 'raider' },
    raid_days: ['wednesday'],
    officer_days: [],
    day_names: NAMES,
    ...over
  };
}

const labels = (menus: Menus, label: string) =>
  menus.menus.find((m) => m.label === label)?.groups.map((g) => g.map((l) => l.label)) ?? null;
const paths = (menus: Menus, label: string) =>
  menus.menus.find((m) => m.label === label)?.groups.flat().map((l) => l.path) ?? [];

describe('menusFor', () => {
  it('gives a visitor the public pages and Discord sign-in, and no Officers menu', () => {
    const m = menusFor(null);
    expect(m.tier).toBe('visitor');
    expect(m.menus.map((x) => x.label)).toEqual(['Hub', 'Me']);
    expect(labels(m, 'Hub')).toEqual([['Home', 'How we raid', 'Hub features', 'Story', 'Recruit']]);
    expect(labels(m, 'Me')).toEqual([[SIGN_IN.label], ['What you can do']]);
    expect(paths(m, 'Me')[0]).toBe('/auth/login');
    expect(m.officerQuickLinks).toEqual([]);
  });

  it("gives a raider during the launch hold only the site's held top bar", () => {
    const m = menusFor(session());
    expect(m.tier).toBe('raider');
    expect(labels(m, 'Hub')?.[0]).toEqual(['Hub home', 'Raid']);
    expect(labels(m, 'Me')).toEqual([['Me'], ['Your setup', 'What you can do'], [SIGN_OUT.label]]);
    expect(labels(m, 'Officers')).toBeNull();
  });

  it("gives an officer the site's officer tools and only the nights they run", () => {
    const m = menusFor(session({ day_roles: { sunday: 'officer' }, raid_days: ['sunday'], officer_days: ['sunday'] }));
    expect(m.tier).toBe('officer');
    const officers = labels(m, 'Officers');
    expect(officers?.[0]).toEqual(OFFICER_MENU.map((i) => i.label));
    expect(officers?.[1]).toEqual(['Sunday officers']);
    expect(officers).toHaveLength(2);
    expect(paths(m, 'Hub')).toContain('/bank');
    expect(labels(m, 'Me')?.[1]).toContain('Account settings');
    expect(m.officerQuickLinks).toEqual([
      { label: 'Officer console', path: '/officers' },
      { label: 'Sunday officers', path: '/officers/nights/sunday' }
    ]);
  });

  it('gives a super admin the officer tools plus the Admin console, outside the tray shortcuts', () => {
    const m = menusFor(
      session({ super_admin: true, global_officer: true, officer_days: ['wednesday', 'sunday'], day_roles: {} })
    );
    expect(m.tier).toBe('admin');
    expect(labels(m, 'Officers')?.at(-1)).toEqual(['Admin console']);
    expect(labels(m, 'Officers')?.[1]).toEqual(['Wednesday officers', 'Sunday officers']);
    expect(m.officerQuickLinks.map((l) => l.path)).not.toContain('/admin');
  });

  it('numbers the hub pages CmdOrCtrl+1.. and the officer tools CmdOrCtrl+Shift+1..', () => {
    const m = menusFor(session({ officer_days: ['wednesday'], day_roles: { wednesday: 'officer' } }));
    const hub = m.menus.find((x) => x.label === 'Hub')!.groups[0];
    expect(hub.map((l) => l.accelerator)).toEqual(hub.map((_, i) => `CmdOrCtrl+${i + 1}`));
    const officers = m.menus.find((x) => x.label === 'Officers')!.groups;
    expect(officers[0][0].accelerator).toBe('CmdOrCtrl+Shift+1');
    expect(officers[1][0].accelerator).toBeUndefined();
    const all = m.menus.flatMap((x) => x.groups.flat()).flatMap((l) => (l.accelerator ? [l.accelerator] : []));
    expect(new Set(all).size).toBe(all.length);
  });
});

it('parseSession accepts a session and nothing else', () => {
  expect(parseSession(session())).toEqual(session());
  expect(parseSession({ detail: 'Not signed in' })).toBeNull();
  expect(parseSession(null)).toBeNull();
  expect(parseSession({ member_id: '1', officer_days: [], raid_days: [] })).toBeNull();
});

describe("the live site's lists and launch hold (/desktop.json)", () => {
  const raider = session();

  it('bundles the site as this build knows it', () => {
    expect(BUNDLED_SITE).toEqual(desktopSite());
    expect(menusFor(raider, BUNDLED_SITE)).toEqual(menusFor(raider));
  });

  it('opens a raider\'s menus as soon as the site lifts the launch hold, without a new release', () => {
    const m = menusFor(raider, desktopSite(false));
    expect(labels(m, 'Hub')?.[0]).toEqual(['Hub home', 'Raid', 'Logs', 'Highlights', 'Bank']);
    expect(labels(m, 'Me')?.[1]).toEqual(ACCOUNT_MENU.map((i) => i.label));
  });

  it('shows a page the site adds to a menu, and drops one it removes', () => {
    const nav = {
      ...NAV,
      hubMenu: [...NAV.hubMenu.filter((i) => i.href !== '/bank'), { href: '/toolkit', label: 'Toolkit' }],
      memberNav: [...NAV.memberNav, { href: '/toolkit', label: 'Toolkit' }],
      officerMenu: [...NAV.officerMenu, { href: '/officers/reference', label: 'Reference raids' }]
    };
    const m = menusFor(session({ day_roles: { sunday: 'officer' }, raid_days: ['sunday'], officer_days: ['sunday'] }), {
      ...desktopSite(false),
      nav
    });
    expect(paths(m, 'Hub')).toContain('/toolkit');
    expect(paths(m, 'Hub')).not.toContain('/bank');
    expect(labels(m, 'Officers')?.[0].at(-1)).toBe('Reference raids');
  });

  it("words the account menu as the site does, with the site's Log out", () => {
    const m = menusFor(session({ officer_days: ['wednesday'], day_roles: { wednesday: 'officer' } }));
    const me = m.menus.find((x) => x.label === 'Me')!.groups;
    expect(me[1].map((l) => [l.label, l.path])).toEqual(ACCOUNT_MENU.map((i) => [i.label, i.href]));
    expect(me.at(-1)).toEqual([{ label: SIGN_OUT.label, path: SIGN_OUT.href, signOut: true }]);
  });
});
