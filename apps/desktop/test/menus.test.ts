import { describe, expect, it } from 'vitest';
import type { Session } from '../../web/src/lib/api';
import { OFFICER_MENU } from '../../web/src/lib/nav';
import { menusFor, parseSession, type Menus } from '../src/menus';

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
    expect(labels(m, 'Me')).toEqual([['Sign in with Discord'], ['What you can do']]);
    expect(paths(m, 'Me')[0]).toBe('/auth/login');
    expect(m.officerQuickLinks).toEqual([]);
  });

  it("gives a raider during the launch hold only the site's held top bar", () => {
    const m = menusFor(session());
    expect(m.tier).toBe('raider');
    expect(labels(m, 'Hub')?.[0]).toEqual(['Hub home', 'Raid']);
    expect(labels(m, 'Me')).toEqual([['Me'], ['Your setup', 'What you can do']]);
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
