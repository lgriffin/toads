import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { APPS, TIERS, rank, standing, tierOf, unlocked } from './access';
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
