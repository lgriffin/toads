import { describe, expect, it } from 'vitest';
import {
  ApiError,
  chooseName,
  claimError,
  createClaim,
  getAccountSettings,
  getSession,
  listClaims,
  listMembers,
  removeWclKey,
  saveWclKey,
  settingsError,
  statusLabel,
  unclaim,
  wclKeyLabel
} from './api';

type Call = { url: string; init: RequestInit };

function fakeFetch(status: number, body?: unknown): { f: typeof fetch; calls: Call[] } {
  const calls: Call[] = [];
  const f = (async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    return new Response(body === undefined ? null : JSON.stringify(body), { status });
  }) as unknown as typeof fetch;
  return { f, calls };
}

describe('getSession', () => {
  it('returns the member', async () => {
    const { f } = fakeFetch(200, {
      member_id: 1,
      display_name: 'Hopscotch',
      global_officer: false,
      day_roles: {},
      raid_days: [],
      officer_days: []
    });
    expect((await getSession(f))?.display_name).toBe('Hopscotch');
  });
  it('returns null when signed out', async () => {
    expect(await getSession(fakeFetch(401, { detail: 'Not signed in' }).f)).toBeNull();
  });
  it('throws on other errors', async () => {
    await expect(getSession(fakeFetch(503, { detail: 'Discord is unavailable' }).f)).rejects.toThrow('Discord');
  });
});

describe('claims', () => {
  it('posts the character id only', async () => {
    const { f, calls } = fakeFetch(201, { id: 3, status: 'pending' });
    await createClaim(42, f);
    expect(calls[0].url).toBe('/api/claims');
    expect(calls[0].init.method).toBe('POST');
    expect(JSON.parse(String(calls[0].init.body))).toEqual({ character_id: 42 });
  });
  it('lists members', async () => {
    const { f, calls } = fakeFetch(200, [{ member_id: 1, display_name: 'Hopscotch', discord_user_id: null }]);
    expect((await listMembers(f))[0].display_name).toBe('Hopscotch');
    expect(calls[0].url).toBe('/api/members');
  });
  it('lists and unclaims', async () => {
    expect(await listClaims(fakeFetch(200, []).f)).toEqual([]);
    const { f, calls } = fakeFetch(204);
    await unclaim(7, f);
    expect(calls[0]).toMatchObject({ url: '/api/claims/7', init: { method: 'DELETE' } });
  });
  it('keeps the status text for non-JSON errors', async () => {
    const f = (async () => new Response('oops', { status: 500, statusText: 'Server Error' })) as unknown as typeof fetch;
    await expect(listClaims(f)).rejects.toMatchObject({ status: 500, message: 'Server Error' });
  });
});

describe('messages', () => {
  it('explains each refusal', () => {
    expect(claimError(new ApiError(401, ''))).toMatch(/Sign in/);
    expect(claimError(new ApiError(403, ''))).toMatch(/trial or raider/);
    expect(claimError(new ApiError(404, ''))).toMatch(/No character/);
    expect(claimError(new ApiError(409, ''))).toMatch(/officer/);
    expect(claimError(new ApiError(500, 'boom'))).toBe('boom');
    expect(claimError(new Error('x'))).toMatch(/try again/);
  });
  it('labels claim states', () => {
    expect(statusLabel({ status: 'approved', reason: null })).toBe('Approved');
    expect(statusLabel({ status: 'pending', reason: null })).toMatch(/officer/);
    expect(statusLabel({ status: 'rejected', reason: 'Not yours' })).toBe('Rejected: Not yours');
    expect(statusLabel({ status: 'rejected', reason: null })).toBe('Rejected');
  });
});

describe('account settings', () => {
  const settings = {
    shown_name: 'Hops',
    name_source: 'discord',
    name_character_id: null,
    name_options: [{ source: 'discord', name: 'Hops', character_id: null }],
    wcl_key: null,
    wcl_key_in_use: 'guild'
  };
  it('reads settings', async () => {
    const { f, calls } = fakeFetch(200, settings);
    expect((await getAccountSettings(f)).shown_name).toBe('Hops');
    expect(calls[0].url).toBe('/api/me/settings');
  });
  it('puts the chosen name', async () => {
    const { f, calls } = fakeFetch(200, settings);
    await chooseName({ source: 'character', character_id: 2 }, f);
    expect(calls[0].init.method).toBe('PUT');
    expect(JSON.parse(String(calls[0].init.body))).toEqual({ source: 'character', character_id: 2 });
  });
  it('puts and deletes the key', async () => {
    const { f, calls } = fakeFetch(200, settings);
    await saveWclKey('id-1234', 'the-secret', f);
    await removeWclKey(f);
    expect(calls.map((c) => [c.url, c.init.method])).toEqual([
      ['/api/me/wcl-key', 'PUT'],
      ['/api/me/wcl-key', 'DELETE']
    ]);
    expect(JSON.parse(String(calls[0].init.body))).toEqual({ client_id: 'id-1234', client_secret: 'the-secret' });
  });
  it('describes the key without revealing it', () => {
    expect(wclKeyLabel({ wcl_key: null })).toContain('guild key');
    const key = { client_id_hint: 'ab12', updated_at: '', checked_at: null };
    expect(wclKeyLabel({ wcl_key: { ...key, status: 'working' } })).toContain('ending ab12');
    expect(wclKeyLabel({ wcl_key: { ...key, status: 'rejected' } })).toContain('refused');
  });
  it('explains failures', () => {
    expect(settingsError(new ApiError(401, 'Not signed in'))).toContain('Sign in');
    expect(settingsError(new ApiError(422, 'Choose one of your approved characters'))).toContain('approved');
    expect(settingsError(new Error('x'))).toContain('try again');
  });
});
