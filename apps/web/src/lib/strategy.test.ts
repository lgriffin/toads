import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { ApiError } from './api';
import { docProblem, hubStrategy, pinnedLine, strategyError } from './strategy';
import { PREVIEW_RAIDS, previewStrategy } from './preview/strategy-fake';

const DOC = 'https://docs.google.com/document/d/';

describe('strategy docs', () => {
  it('takes only https Google Docs and Drive links, as the API does', () => {
    expect(docProblem(`${DOC}abc/edit`)).toBeNull();
    expect(docProblem('https://drive.google.com/file/d/abc/view', 'Naxx')).toBeNull();
    for (const bad of ['', '   ', 'http://docs.google.com/document/d/x', 'https://example.com/doc', 'not a link',
      'https://docs.google.com.evil.example/x', 'https://user:pw@docs.google.com/x', `${DOC}${'x'.repeat(500)}`]) {
      expect(docProblem(bad), bad).not.toBeNull();
    }
    expect(docProblem(`${DOC}abc`, 'x'.repeat(81))).toMatch(/80 characters/);
  });

  it('lists the same raids as the hub, in its order', () => {
    const service = readFileSync(
      new URL('../../../../services/api/src/toads_api/strategy/service.py', import.meta.url),
      'utf8'
    );
    const raids = [...service.matchAll(/Raid\("([a-z0-9]+)", "([^"]+)", "([^"]+)"\)/g)].map(([, id, short, name]) => ({ id, short, name }));
    expect(PREVIEW_RAIDS).toEqual(raids);
  });

  it('says who pinned a doc, and when', () => {
    expect(pinnedLine({ added_at: '2026-10-22T18:00:00Z', added_by: 'Hopscotch' })).toBe('Pinned 22 Oct by Hopscotch');
    expect(pinnedLine({ added_at: '2026-10-22T18:00:00Z', added_by: null })).toBe('Pinned 22 Oct');
  });

  it('explains refusals', () => {
    expect(strategyError(new ApiError(403, 'Forbidden'))).toMatch(/Only officers/);
    expect(strategyError(new ApiError(404, 'gone'))).toMatch(/taken it down/);
    expect(strategyError(new ApiError(422, 'Pick one of the raids'))).toBe('Pick one of the raids');
    expect(strategyError(new ApiError(500, ''))).toMatch(/try again/);
    expect(strategyError(new Error('boom'))).toMatch(/try again/);
  });

  it('calls the hub routes', async () => {
    const calls: [string, RequestInit | undefined][] = [];
    const f = (async (path: string, init?: RequestInit) => {
      calls.push([path, init]);
      return new Response(init?.method === 'DELETE' ? null : '{}', { status: init?.method === 'DELETE' ? 204 : 200 });
    }) as typeof fetch;
    const hub = hubStrategy(f);
    await hub.library();
    await hub.pin('naxx', `${DOC}1`, '', null);
    await hub.remove(7, null);
    await hub.pin('naxx', `${DOC}1`, '', 'wed');
    await hub.remove(7, 'wed');
    await hub.night('wed');
    await hub.setNight('wed', 'bwl');
    expect(calls.map(([p, i]) => `${i?.method ?? 'GET'} ${p}`)).toEqual([
      'GET /api/strategy',
      'POST /api/admin/strategy',
      'DELETE /api/admin/strategy/7',
      'POST /api/days/wed/strategy/docs',
      'DELETE /api/days/wed/strategy/docs/7',
      'GET /api/days/wed/strategy',
      'PUT /api/days/wed/strategy'
    ]);
    expect(JSON.parse(String(calls[6][1]?.body))).toEqual({ raid: 'bwl' });
  });

  it('works the preview from samples', async () => {
    const wed = await previewStrategy.night('wed');
    expect(wed.raid?.short).toBe('BWL');
    expect(wed.pinned?.title).toBe('BWL full clear');
    const pinned = await previewStrategy.pin('naxx', ` ${DOC}naxx `, '  Naxx   full clear ', 'wed');
    expect(pinned.title).toBe('Naxx full clear');
    expect((await previewStrategy.pin('aq40', `${DOC}aq`, '', null)).title).toBe("Temple of Ahn'Qiraj strategy");
    await expect(previewStrategy.pin('naxx', 'https://example.com', '', null)).rejects.toBeInstanceOf(ApiError);
    await expect(previewStrategy.pin('kara', `${DOC}k`, '', null)).rejects.toBeInstanceOf(ApiError);
    const naxx = (await previewStrategy.library()).raids.find((r) => r.raid.id === 'naxx');
    expect(naxx?.pinned?.id).toBe(pinned.id);
    await previewStrategy.remove(pinned.id, 'wed');
    await expect(previewStrategy.remove(pinned.id, null)).rejects.toBeInstanceOf(ApiError);
    expect((await previewStrategy.setNight('thu', 'naxx')).pinned).toBeNull();
    expect((await previewStrategy.setNight('thu', null)).raid).toBeNull();
    expect((await previewStrategy.library()).nights.map((n) => n.raid_day)).toContain('thu');
  });
});
