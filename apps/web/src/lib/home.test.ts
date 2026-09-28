import { describe, expect, it } from 'vitest';
import { CATALOGUE, defaultLayout, isAnalyzer, isWide, move, saved, shownIds, toggle } from './home';

describe('home catalogue', () => {
  it('has unique ids', () => {
    expect(new Set(CATALOGUE.map((w) => w.id)).size).toBe(CATALOGUE.length);
  });

  it('keeps officer widgets off a member home', () => {
    expect(defaultLayout(false).widgets.some((w) => w.officer_only)).toBe(false);
    expect(shownIds(defaultLayout(true))).toContain('officer_desk');
  });

  it('shows the defaults and hides the extras', () => {
    const shown = shownIds(defaultLayout(false));
    expect(shown).toEqual([
      'next_raid',
      'guild_snapshot',
      'last_raid',
      'my_performance',
      'raid_totals',
      'recent_raids',
      'raid_activity',
      'healing_weekly',
      'healers_weekly',
      'top_damage',
      'top_healing',
      'attendance',
      'posts',
      'highlights'
    ]);
    expect(defaultLayout(false).customised).toBe(false);
  });

  it('tells hub widgets from analyzer ones', () => {
    expect(CATALOGUE.find((w) => w.id === 'top_damage')?.source).toBe('analyzer');
    expect(CATALOGUE.find((w) => w.id === 'posts')?.source).toBe('hub');
    expect(isAnalyzer('attendance')).toBe(true);
    expect(isAnalyzer('raid_totals')).toBe(false);
  });

  it('marks raid totals and the weekly healing charts as wide', () => {
    expect(isWide('raid_totals')).toBe(true);
    expect(isWide('healing_weekly')).toBe(true);
    expect(isAnalyzer('healers_weekly')).toBe(true);
    expect(isWide('posts')).toBe(false);
  });
});

describe('editing a layout', () => {
  const widgets = defaultLayout(false).widgets;

  it('moves a widget up and down, and not past either end', () => {
    expect(move(widgets, 'guild_snapshot', -1).map((w) => w.id).slice(0, 2)).toEqual(['guild_snapshot', 'next_raid']);
    expect(move(widgets, 'next_raid', -1)).toEqual(widgets);
    expect(move(widgets, 'recruiting', 1)).toEqual(widgets);
  });

  it('toggles one widget without touching the rest', () => {
    const out = toggle(widgets, 'recruiting');
    expect(out.find((w) => w.id === 'recruiting')?.shown).toBe(true);
    expect(out.filter((w) => w.id !== 'recruiting')).toEqual(widgets.filter((w) => w.id !== 'recruiting'));
  });

  it('saves shown widgets first, in order', () => {
    const edited = toggle(move(widgets, 'highlights', -1), 'next_raid');
    const layout = saved(edited);
    expect(layout.customised).toBe(true);
    expect(shownIds(layout).slice(-3)).toEqual(['attendance', 'highlights', 'posts']);
    expect(shownIds(layout)).not.toContain('next_raid');
    expect(layout.widgets.at(-1)?.shown).toBe(false);
  });
});
