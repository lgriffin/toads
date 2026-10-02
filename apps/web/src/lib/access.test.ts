import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import {
  APPS,
  MORE,
  RAID_ROLE_PERMISSIONS,
  TIERS,
  held,
  needsRole,
  raidRoleOf,
  rank,
  standing,
  tierOf,
  unlocked
} from './access';
import type { Session } from './api';

// The hub's RBAC table, read as text so the toolkit cannot drift from it.
const RBAC = readFileSync(
  new URL('../../../../services/api/src/toads_api/rbac/permissions.py', import.meta.url),
  'utf-8'
);

/** Permission member name -> value, e.g. VIEW_BANK -> view_bank. */
const VALUES = new Map([...RBAC.matchAll(/^ {4}([A-Z_]+) = "([a-z_]+)"$/gm)].map((m) => [m[1], m[2]]));

/** The values a role set adds, from `_NAME = ... {Permission.X, ...}` up to the next blank line. */
function added(name: string): Set<string> {
  const block = RBAC.slice(RBAC.indexOf(`\n${name} = `)).split('\n\n')[0];
  return new Set([...block.matchAll(/Permission\.([A-Z_]+)/g)].map((m) => VALUES.get(m[1]) ?? m[1]));
}

const RAIDER = new Set([...added('_MEMBER'), ...added('_TRIAL'), ...added('_RAIDER')]);
const ADMIN_ONLY = added('SUPER_ADMIN_ONLY');

const session = (s: Partial<Session>): Session => ({
  member_id: 1,
  display_name: 'Hopscotch',
  global_officer: false,
  day_roles: {},
  raid_days: [],
  officer_days: [],
  ...s
});

describe('the toolkit follows the RBAC table', () => {
  const rows = APPS.flatMap((a) => a.rows.flatMap((r) => r.can.map((c) => ({ tier: r.tier, ...c }))));

  it('reads the table', () => {
    expect(VALUES.get('VIEW_BANK')).toBe('view_bank');
    expect(RAIDER.has('submit_highlight')).toBe(true);
    expect(ADMIN_ONLY).toEqual(new Set(['manage_grants']));
  });

  it('names only permissions the hub has', () => {
    const known = new Set(VALUES.values());
    for (const r of rows) if (r.permission) expect(known, r.text).toContain(r.permission);
  });

  it('puts each permission in the tier that first holds it', () => {
    for (const r of rows.filter((x) => x.permission)) {
      const p = r.permission as string;
      // Applying is open to anyone in the Discord server, so the toolkit shows it to visitors.
      const tier = p === 'apply' ? 'visitor' : ADMIN_ONLY.has(p) ? 'admin' : RAIDER.has(p) ? 'raider' : 'officer';
      expect(r.tier, r.text).toBe(tier);
    }
  });

  it('knows what a trial and a raider role add', () => {
    // One assignment only: `_TRIAL = _MEMBER | {...}` and `_RAIDER = _TRIAL | {...}` sit on consecutive lines.
    const own = (name: string) => {
      const stmt = RBAC.slice(RBAC.indexOf(`\n${name} = `) + 1).split(/\n(?=[A-Z_]+ = )|\n\n/)[0];
      return [...stmt.matchAll(/Permission\.([A-Z_]+)/g)].map((m) => VALUES.get(m[1]) ?? m[1]);
    };
    const trial = own('_TRIAL');
    expect([...RAID_ROLE_PERMISSIONS.trial].sort()).toEqual([...trial].sort());
    expect([...RAID_ROLE_PERMISSIONS.raider].sort()).toEqual([...trial, ...own('_RAIDER')].sort());
  });

  it('says only super admins hand out bank tokens', () => {
    expect(MORE.find((m) => m.title === 'Bank helper')?.body).toMatch(/super admin/);
  });

  it('covers every app at every tier', () => {
    for (const app of APPS) expect(app.rows.map((r) => r.tier)).toEqual([...TIERS]);
  });
});

describe('tiers', () => {
  it('reads the session', () => {
    expect(tierOf(null)).toBe('visitor');
    expect(tierOf(session({}))).toBe('raider');
    expect(tierOf(session({ raid_days: ['wed'], day_roles: { wed: 'trial' } }))).toBe('raider');
    expect(tierOf(session({ officer_days: ['wed'] }))).toBe('officer');
    expect(tierOf(session({ global_officer: true }))).toBe('officer');
    expect(tierOf(session({ global_officer: true, super_admin: true }))).toBe('admin');
  });

  it('reads the best raid role', () => {
    expect(raidRoleOf(null)).toBe('member');
    expect(raidRoleOf(session({}))).toBe('member');
    expect(raidRoleOf(session({ day_roles: { wed: 'trial' } }))).toBe('trial');
    expect(raidRoleOf(session({ day_roles: { wed: 'trial', sun: 'raider' } }))).toBe('raider');
    expect(raidRoleOf(session({ day_roles: { wed: 'officer' } }))).toBe('raider');
    expect(raidRoleOf(session({ global_officer: true }))).toBe('raider');
  });

  it('marks raider rows a member or trial does not hold yet', () => {
    const claim = { text: 'Claim', permission: 'claim_character' };
    const clip = { text: 'Clip', permission: 'submit_highlight' };
    const bank = { text: 'Bank', permission: 'view_bank' };
    expect(needsRole(claim)).toBe('trial');
    expect(needsRole(clip)).toBe('raider');
    expect(needsRole(bank)).toBeNull();
    expect(needsRole({ text: 'App' })).toBeNull();
    expect(held(bank, 'member')).toBe(true);
    expect(held(claim, 'member')).toBe(false);
    expect(held(claim, 'trial')).toBe(true);
    expect(held(clip, 'trial')).toBe(false);
    expect(held(clip, 'raider')).toBe(true);
  });

  it('unlocks rows up to the viewer', () => {
    const row = { tier: 'officer' as const, can: [] };
    expect(unlocked(row, 'raider')).toBe(false);
    expect(unlocked(row, 'officer')).toBe(true);
    expect(unlocked(row, 'admin')).toBe(true);
    expect(rank('visitor')).toBe(0);
  });

  it('says where each tier stands', () => {
    for (const t of TIERS) expect(standing(t).length).toBeGreaterThan(20);
  });
});
