import { describe, expect, it } from 'vitest';
import {
  myCharacterPage,
  myRaidLine,
  placeLabel,
  rolesLabel,
  showTrends,
  spreadValue,
  vsMedian,
  FLASK_METRIC,
  type CharacterRaid,
  type Spread
} from './characters';
import { previewCharacterPage, previewRaidLine } from './mock/characters';

const raid = (over: Partial<CharacterRaid> = {}): CharacterRaid => ({
  report_id: 'abc',
  title: 'SSC',
  zone: 'Serpentshrine Cavern',
  raid_date: '2026-10-14 20:00:00',
  weekday: 2,
  role: 'healer',
  metric: 'Healing',
  value: 1_100_000,
  display: '1.1M',
  median: 1_000_000,
  median_display: '1.0M',
  rank: 2,
  of: 6,
  percent: 18.2,
  ...over
});

const spread = (name: string, over: Partial<Spread> = {}): Spread => ({
  name,
  min: 0,
  mean: 0,
  max: 0,
  raids: 3,
  total: 0,
  role: '',
  raids_used: 3,
  ...over
});

describe('character pages', () => {
  it('reads each raid against the median for its role', () => {
    expect(vsMedian(raid())).toEqual({ label: '+10%', better: true });
    expect(vsMedian(raid({ value: 900_000 }))).toEqual({ label: '-10%', better: false });
    expect(vsMedian(raid({ median: null }))).toBeNull();
  });

  it('counts less damage taken as better for a tank', () => {
    expect(vsMedian(raid({ role: 'tank', value: 900_000 }))).toEqual({ label: '-10%', better: true });
    expect(vsMedian(raid({ role: 'tank', value: 1_200_000 }))).toEqual({ label: '+20%', better: false });
  });

  it('names a place in the role, and none when unknown', () => {
    expect(placeLabel(raid())).toBe('2nd of 6');
    expect(placeLabel(raid({ rank: 11, of: 12 }))).toBe('11th of 12');
    expect(placeLabel(raid({ rank: 23, of: 25 }))).toBe('23rd of 25');
    expect(placeLabel(raid({ rank: 0, of: 0 }))).toBe('');
  });

  it('lists roles most played first', () => {
    expect(rolesLabel({ ranged: 2, healer: 9 })).toBe('Healer 9 · Ranged 2');
  });

  it('writes spreads as the analyzer does', () => {
    expect(spreadValue(spread('Healing'), 12_345_678)).toBe('12.3M');
    expect(spreadValue(spread('Total casts'), 950)).toBe('950');
    expect(spreadValue(spread('Overheal %'), 18.25)).toBe('18.3%');
    expect(spreadValue(spread(FLASK_METRIC), 0.8)).toBe('80%');
  });

  it('draws trends from three raids, and says the history is building before that', () => {
    expect(showTrends(previewCharacterPage('Hopscotch').page!)).toBe(true);
    expect(showTrends(previewCharacterPage('Lilypadd').page!)).toBe(false);
  });

  it('asks for a named character only when one is picked', async () => {
    const seen: string[] = [];
    const f = (async (url: string) => {
      seen.push(url);
      return new Response(JSON.stringify(previewCharacterPage()), { status: 200, headers: { 'content-type': 'application/json' } });
    }) as unknown as typeof fetch;
    await myCharacterPage(null, f);
    await myCharacterPage('Lily pad', f);
    expect(seen).toEqual(['/api/me/character-page', '/api/me/character-page?name=Lily%20pad']);
  });
});

describe('a member\'s line on a raid log', () => {
  it('asks the API for the member\'s own line on that raid', async () => {
    const urls: string[] = [];
    const line = { name: 'Lilypadd', raid: previewCharacterPage('Lilypadd').page!.recent[0] };
    const f = (async (url: string) => {
      urls.push(url);
      return new Response(JSON.stringify({ line: url.includes('nobody') ? null : line }), {
        status: 200,
        headers: { 'content-type': 'application/json' }
      });
    }) as typeof fetch;
    expect(await myRaidLine('pondThu1015', f)).toMatchObject({ name: 'Lilypadd', raid: { role: 'healer' } });
    expect(await myRaidLine('nobody here', f)).toBeNull();
    expect(urls.map((u) => u.split('/api')[1])).toEqual(['/me/raid-line?report=pondThu1015', '/me/raid-line?report=nobody%20here']);
  });

  it('finds the preview member\'s main in the raid, or another of their characters, or nobody', async () => {
    expect(await previewRaidLine('pondWed1014')).toMatchObject({ name: 'Hopscotch', raid: { rank: 2, of: 3 } });
    expect(await previewRaidLine('pondThu1015')).toMatchObject({ name: 'Lilypadd', raid: { role: 'healer' } });
    expect(await previewRaidLine('somebodyElses')).toBeNull();
  });
});
