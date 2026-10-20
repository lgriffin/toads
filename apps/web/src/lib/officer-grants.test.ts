import { describe, expect, it, vi } from 'vitest';
import { ApiError } from './api';
import { byMember, grantLabel, grantPhrase, holds, hubOfficerGrants, officerGrantError, type OfficerGrant } from './officer-grants';
import { previewOfficerGrants } from './preview/officer-grants-fake';

const DAYS = [
  { id: 'wed', name: 'Wednesday' },
  { id: 'sun', name: 'Sunday' }
];
const grant = (id: number, user: string, raid_day: string | null): OfficerGrant => ({
  id,
  discord_user_id: user,
  username: `u${user}`,
  display_name: `U${user}`,
  raid_day,
  granted_by_name: null,
  granted_at: '2026-10-20T12:00:00Z'
});

describe('officer grants', () => {
  it('names what a grant makes its holder', () => {
    expect(grantLabel('sun', DAYS)).toBe('Sunday officer');
    expect(grantLabel(null, DAYS)).toBe('Global officer');
    expect(grantLabel('fri', DAYS)).toBe('fri officer');
    expect(grantPhrase('sun', DAYS)).toBe('a Sunday officer');
    expect(grantPhrase(null, DAYS)).toBe('a global officer');
  });

  it('groups grants by member and knows what is held', () => {
    const grants = [grant(1, '7', 'wed'), grant(2, '8', null), grant(3, '7', 'sun')];
    expect(byMember(grants).map((g) => [g.member.discord_user_id, g.grants.map((x) => x.id)])).toEqual([
      ['7', [1, 3]],
      ['8', [2]]
    ]);
    expect(holds(grants, '8', null)).toBe(true);
    expect(holds(grants, '8', 'wed')).toBe(false);
  });

  it('calls the super admins’ routes', async () => {
    const f = vi.fn(async () => new Response(JSON.stringify({})));
    const hub = hubOfficerGrants(f as unknown as typeof fetch);
    await hub.load();
    await hub.search('rib bit');
    await hub.grant('305', null);
    await hub.revoke(4);
    const calls = f.mock.calls as unknown as [string, RequestInit][];
    expect(calls.map(([p, i]) => [i?.method ?? 'GET', p])).toEqual([
      ['GET', '/api/admin/officer-grants'],
      ['GET', '/api/admin/officer-grants/discord-members?q=rib%20bit'],
      ['POST', '/api/admin/officer-grants'],
      ['DELETE', '/api/admin/officer-grants/4']
    ]);
    expect(JSON.parse(String(calls[2][1].body))).toEqual({ discord_user_id: '305', raid_day: null });
  });

  it('the preview grants once and revokes', async () => {
    const fake = previewOfficerGrants();
    const made = await fake.grant('305', 'wed');
    expect((await fake.grant('305', 'wed')).id).toBe(made.id);
    await fake.revoke(made.id);
    await expect(fake.revoke(made.id)).rejects.toThrow();
    expect((await fake.load()).grants.map((g) => g.discord_user_id)).toEqual(['304']);
  });

  it('explains refusals', () => {
    expect(officerGrantError(new ApiError(403, 'Forbidden'))).toContain('super admins');
    expect(officerGrantError(new ApiError(422, 'They are not in the Toads Discord'))).toBe(
      'They are not in the Toads Discord'
    );
    expect(officerGrantError(new Error('x'))).toContain('try again');
  });
});
