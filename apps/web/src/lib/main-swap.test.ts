import { describe, expect, it } from 'vitest';
import { ApiError } from './api';
import { altNamed, characterLabel, hubMain, mainError, sameName } from './main-swap';
import { previewMain } from './preview/main-fake';

describe('main swap', () => {
  it('reads, asks and withdraws through the member’s own routes', async () => {
    const calls: [string, RequestInit | undefined][] = [];
    const f = (async (p: string, i?: RequestInit) => {
      calls.push([p, i]);
      return new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } });
    }) as typeof fetch;
    const hub = hubMain(f);
    await hub.mine();
    await hub.ask(7);
    await hub.withdraw();
    expect(calls.map(([p, i]) => `${i?.method ?? 'GET'} ${p}`)).toEqual([
      'GET /api/me/main',
      'POST /api/me/main',
      'DELETE /api/me/main/request'
    ]);
    expect(calls[1][1]?.body).toBe(JSON.stringify({ character_id: 7 }));
  });

  it('labels the main in the dropdown and finds alts by name as the hub compares them', async () => {
    expect(characterLabel('Hopscotch', 'hopscotch')).toBe('Hopscotch (main)');
    expect(characterLabel('Lilypadd', 'Hopscotch')).toBe('Lilypadd');
    expect(characterLabel('Lilypadd', null)).toBe('Lilypadd');
    expect(sameName('Höpscotch', 'Hopscotch')).toBe(false);
    const mine = await previewMain.mine();
    expect(altNamed(mine, 'lilypadd')?.character_id).toBe(2);
    expect(altNamed(mine, 'Hopscotch')).toBeUndefined();
  });

  it('keeps one pending ask in the preview, and refuses the main itself', async () => {
    await expect(previewMain.ask(1)).rejects.toMatchObject({ status: 409 });
    expect((await previewMain.ask(2)).status).toBe('pending');
    expect((await previewMain.ask(3)).character_name).toBe('Bogwalker');
    expect((await previewMain.mine()).request?.character_name).toBe('Bogwalker');
    await previewMain.withdraw();
    expect((await previewMain.mine()).request).toBeNull();
    await expect(previewMain.withdraw()).rejects.toMatchObject({ status: 404 });
  });

  it('tells a member why an ask failed', () => {
    expect(mainError(new ApiError(422, 'x'))).toMatch(/approved as yours/);
    expect(mainError(new ApiError(409, 'x'))).toMatch(/already your main/);
    expect(mainError(new Error('boom'))).toBe('Something went wrong; try again.');
  });
});
