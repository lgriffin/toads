import { describe, expect, it } from 'vitest';
import { ANALYZER_WIDGETS, CATALOGUE, defaultLayout, isWide, move, saved, shownIds, toggle } from './home';

describe('home catalogue', () => {
  it('has unique ids', () => {
    expect(new Set(CATALOGUE.map((w) => w.id)).size).toBe(CATALOGUE.length);
  });

  it('keeps officer widgets off a member home', () => {
    expect(defaultLayout(false).widgets.some((w) => w.officer_only)).toBe(false);
    expect(shownIds(defaultLayout(true))).toContain('officer_desk');
  });

  it('marks the badge roster for raid leaders only', () => {
    expect(ANALYZER_WIDGETS.find((w) => w.id === 'badges')?.officer_only).toBe(true);
  });

  it('leaves the analyzer raid widgets to Logs', () => {
    const ids = defaultLayout(true).widgets.map((w) => w.id);
    for (const w of ANALYZER_WIDGETS) expect(ids).not.toContain(w.id);
    expect(CATALOGUE.every((w) => w.source === 'hub')).toBe(true);
    expect(ANALYZER_WIDGETS.every((w) => w.source === 'analyzer')).toBe(true);
  });

  it('shows the defaults and hides the extras', () => {
    const shown = shownIds(defaultLayout(false));
    expect(shown).toEqual(['my_performance', 'next_raid', 'raid_totals', 'posts', 'highlights']);
    expect(defaultLayout(false).customised).toBe(false);
  });

  it('marks raid totals and the weekly healing charts as wide', () => {
    expect(isWide('raid_totals')).toBe(true);
    expect(isWide('my_performance')).toBe(true);
    expect(isWide('healing_weekly')).toBe(true);
    expect(isWide('posts')).toBe(false);
  });
});

describe('editing a layout', () => {
  const widgets = defaultLayout(false).widgets;

  it('moves a widget up and down, and not past either end', () => {
    expect(move(widgets, 'next_raid', -1).map((w) => w.id).slice(0, 2)).toEqual(['next_raid', 'my_performance']);
    expect(move(widgets, 'my_performance', -1)).toEqual(widgets);
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
    expect(shownIds(layout).slice(-3)).toEqual(['raid_totals', 'highlights', 'posts']);
    expect(shownIds(layout)).not.toContain('next_raid');
    expect(layout.widgets.at(-1)?.shown).toBe(false);
  });
});
