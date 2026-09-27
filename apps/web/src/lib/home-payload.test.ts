import { describe, expect, it } from 'vitest';
import { barPercent, linkTarget, widgetById, type AnalyzerPage } from './home-payload';

describe('analyzer payload links', () => {
  const raid = (report_id: string) => ({ kind: 'raid' as const, params: { report_id } });

  it('opens a raid on Warcraft Logs, since the live hub has no raid page yet', () => {
    expect(linkTarget(raid('aBcD1234eFgH5678'), '')).toEqual({
      href: 'https://classic.warcraftlogs.com/reports/aBcD1234eFgH5678',
      external: true
    });
  });
  it('opens the sample raid page in the preview', () => {
    expect(linkTarget(raid('ssc-0924'), '/toads', true)).toEqual({ href: '/toads/raids/ssc-0924', external: false });
  });
  it('refuses raid ids that are not id-shaped', () => {
    expect(linkTarget(raid('../admin'), '')).toBeNull();
    expect(linkTarget(raid('../admin'), '', true)).toBeNull();
    expect(linkTarget({ kind: 'raid', params: {} }, '')).toBeNull();
  });
  it('drops links the hub has no page for', () => {
    expect(linkTarget({ kind: 'character', params: { name: 'Hopscotch' } }, '')).toBeNull();
    expect(linkTarget({ kind: 'player_page', params: { name: 'x', server: 'y', region: 'eu' } }, '')).toBeNull();
    expect(linkTarget(null, '')).toBeNull();
  });
});

describe('bars', () => {
  const bars = [
    { label: 'a', value: 2, display: '2' },
    { label: 'b', value: 4, display: '4' }
  ];
  it('scales against the largest value', () => {
    expect(barPercent(bars, 2)).toBe(50);
    expect(barPercent(bars, 4)).toBe(100);
  });
  it('draws nothing when every value is zero', () => {
    expect(barPercent([{ label: 'a', value: 0, display: '0' }], 0)).toBe(0);
  });
});

it('finds a widget by id', () => {
  const page: AnalyzerPage = { version: 1, generated_at: null, widgets: [] };
  expect(widgetById(page, 'last_raid')).toBeNull();
  expect(widgetById(null, 'last_raid')).toBeNull();
});
