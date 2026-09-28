import { describe, expect, it } from 'vitest';
import { MAX_X_LABELS, PALETTE, VIEW, colours, compact, drawable, layout, type ChartPayload } from './charts';

function chart(overrides: Partial<ChartPayload> = {}): ChartPayload {
  return {
    version: 1,
    id: 'healing_weekly',
    title: 'Weekly healing',
    kind: 'bar',
    subtitle: '',
    x_label: 'Week starting',
    y_label: 'Healing per raid',
    categories: ['7 Sep', '14 Sep', '21 Sep'],
    series: [
      {
        key: 'healing_per_raid',
        name: 'Healing per raid',
        values: [1_000_000, null, 2_000_000],
        display: ['1.0M', '-', '2.0M'],
        emphasis: true
      }
    ],
    y_max: 2_000_000,
    references: [{ key: 'target', label: 'Target', value: 1_000_000, display: '1.0M' }],
    notes: [],
    empty: '',
    ...overrides
  };
}

const bottom = VIEW.height - VIEW.bottom;

describe('which charts the hub draws', () => {
  it('draws a chart of its version within the limits', () => {
    expect(drawable(chart())).toBe(true);
  });
  it('refuses other versions, missing charts and oversized or misaligned ones', () => {
    expect(drawable(chart({ version: 2 }))).toBe(false);
    expect(drawable(null)).toBe(false);
    expect(drawable(chart({ categories: Array(53).fill('w'), series: [] }))).toBe(false);
    const s = chart().series[0];
    expect(drawable(chart({ series: Array.from({ length: 9 }, (_, i) => ({ ...s, key: `s${i}` })) }))).toBe(false);
    expect(drawable(chart({ references: Array(4).fill(chart().references[0]) }))).toBe(false);
    expect(drawable(chart({ series: [{ ...s, values: [1] }] }))).toBe(false);
  });
});

describe('bar layout', () => {
  const l = layout(chart());

  it('leaves out gaps and puts bars on the baseline, scaled to y_max', () => {
    expect(l.bars).toHaveLength(2);
    const [low, high] = l.bars;
    expect(low.y + low.height).toBeCloseTo(bottom);
    expect(high.y).toBeCloseTo(VIEW.top);
    expect(low.height).toBeCloseTo(high.height / 2);
    expect(low.x).toBeLessThan(high.x);
  });
  it('gives each bar a tooltip with the formatted number', () => {
    expect(l.bars[1].tip).toBe('Healing per raid, 21 Sep: 2.0M');
  });
  it('draws references across the plot at their value', () => {
    expect(l.references[0].y).toBeCloseTo((VIEW.top + bottom) / 2);
    expect(l.references[0].display).toBe('1.0M');
  });
  it('labels the y axis from 0 to y_max', () => {
    expect(l.yTicks.map((t) => t.label)).toEqual(['0', '500.0K', '1.0M', '1.5M', '2.0M']);
  });
});

describe('line layout', () => {
  it('breaks a line at a gap and keeps lone points as markers', () => {
    const l = layout(
      chart({
        kind: 'line',
        categories: ['a', 'b', 'c', 'd', 'e'],
        series: [
          { key: 'holy', name: 'Holy', values: [1, 2, null, 4, 5], display: ['1', '2', '-', '4', '5'], emphasis: false },
          { key: 'disc', name: 'Disc', values: [null, 3, null, null, null], display: ['-', '3', '-', '-', '-'], emphasis: false }
        ],
        y_max: 5,
        references: []
      })
    );
    const [holy, disc] = l.lines;
    expect(holy.paths).toHaveLength(2);
    expect(holy.paths[0].startsWith('M')).toBe(true);
    expect(holy.points).toHaveLength(4);
    expect(disc.paths).toHaveLength(0);
    expect(disc.points).toHaveLength(1);
    expect(l.bars).toHaveLength(0);
    expect(l.legend.map((e) => e.name)).toEqual(['Holy', 'Disc']);
  });
});

describe('axis labels', () => {
  it('labels at most a handful of categories, always including the newest', () => {
    const categories = Array.from({ length: 26 }, (_, i) => `w${i}`);
    const l = layout(chart({ categories, series: [], references: [] }));
    expect(l.xLabels.length).toBeLessThanOrEqual(MAX_X_LABELS);
    expect(l.xLabels.at(-1)?.label).toBe('w25');
  });
  it('labels every category of a short chart', () => {
    expect(layout(chart()).xLabels.map((x) => x.label)).toEqual(['7 Sep', '14 Sep', '21 Sep']);
  });
  it('copes with a chart of zeros', () => {
    const l = layout(chart({ y_max: 0, references: [], series: [{ ...chart().series[0], values: [0, null, 0] }] }));
    expect(l.bars.every((b) => b.height === 0)).toBe(true);
  });
});

describe('colours', () => {
  it('gives the emphasised series the accent and the rest the palette in order', () => {
    const s = chart().series[0];
    const plain = { ...s, emphasis: false };
    expect(colours([plain, s, plain], 'gold')).toEqual([PALETTE[0], 'gold', PALETTE[1]]);
  });
});

it('formats axis numbers like the analyzer', () => {
  expect([0, 950, 4_500, 12_345_678, 2e9].map(compact)).toEqual(['0', '950', '4.5K', '12.3M', '2.0B']);
});
