import { describe, expect, it } from 'vitest';
import { ApiError } from './api';
import { claimsError, hubClaims } from './officer-claims';
import { previewClaims } from './preview/claims-fake';

describe('officer claims', () => {
  it('calls a night\'s routes, and the global tier\'s for members on no night', async () => {
    const calls: [string, RequestInit | undefined][] = [];
    const f = (async (p: string, i?: RequestInit) => {
      calls.push([p, i]);
      return new Response('[]', { status: 200, headers: { 'content-type': 'application/json' } });
    }) as typeof fetch;
    const hub = hubClaims(f);
    await hub.queue('wed');
    await hub.approve('wed', 7);
    await hub.reject('sun', 8, 'Not theirs');
    await hub.queue(null);
    await hub.approve(null, 9);
    expect(calls.map(([p, i]) => `${i?.method ?? 'GET'} ${p}`)).toEqual([
      'GET /api/days/wed/claims',
      'POST /api/days/wed/claims/7/approve',
      'POST /api/days/sun/claims/8/reject',
      'GET /api/admin/claims',
      'POST /api/admin/claims/9/approve'
    ]);
    expect(calls[2][1]?.body).toBe(JSON.stringify({ reason: 'Not theirs' }));
  });

  it('tells an officer why a decision failed', () => {
    expect(claimsError(new ApiError(403, 'Forbidden'))).toMatch(/this raid night’s officers/);
    expect(claimsError(new ApiError(409, 'Claim is not pending'))).toMatch(/already decided/);
    expect(claimsError(new Error('boom'))).toBe('Something went wrong; try again.');
  });

  it('lists the preview\'s claims by the claimant\'s nights', async () => {
    const wed = await previewClaims.queue('wed');
    expect(wed.map((c) => c.character_name)).toEqual(['Toadstool', 'Lilypadd']);
    expect((await previewClaims.queue(null)).map((c) => c.character_name)).toEqual(['Marshmallow']);
    await expect(previewClaims.approve('thu', wed[0].id)).rejects.toMatchObject({ status: 403 });
    await expect(previewClaims.reject('wed', wed[0].id, ' ')).rejects.toMatchObject({ status: 422 });
    expect((await previewClaims.approve('wed', wed[0].id)).status).toBe('approved');
    expect((await previewClaims.queue('wed')).map((c) => c.character_name)).toEqual(['Lilypadd']);
  });
});
