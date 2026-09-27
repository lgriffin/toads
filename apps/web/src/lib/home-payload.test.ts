import { describe, expect, it } from 'vitest';
import { barPercent, linkHref, widgetById, type AnalyzerPage } from './home-payload';

describe('analyzer payload links', () => {
  it('sends raid links to the raid page', () => {
    expect(linkHref({ kind: 'raid', params: { report_id: 'aBcD1234' } }, '/toads')).toBe('/toads/raids/aBcD1234');
  });
  it('refuses raid ids that are not id-shaped', () => {
    expect(linkHref({ kind: 'raid', params: { report_id: '../admin' } }, '')).toBeNull();
    expect(linkHref({ kind: 'raid', params: {} }, '')).toBeNull();
  });
  it('drops links the hub has no page for', () => {
    expect(linkHref({ kind: 'character', params: { name: 'Hopscotch' } }, '')).toBeNull();
    expect(linkHref({ kind: 'player_page', params: { name: 'x', server: 'y', region: 'eu' } }, '')).toBeNull();
    expect(linkHref(null, '')).toBeNull();
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
