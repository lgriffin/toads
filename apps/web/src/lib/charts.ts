/**
 * Chart payloads from the analyzer (wcl_app.charts; contract in guides/charts.md in lgriffin/warcraftlogs_project)
 * and the geometry the hub draws them with. Standalone: no Svelte, no DOM, so every chart on the hub is laid out
 * the same way and the layout is unit tested. The analyzer decides what a chart shows (which series, the y range,
 * the formatted numbers); this file only decides where things go. The API refuses payloads over the limits, so
 * the limits here only guard against a payload that slipped through.
 */

export const CHART_VERSION = 1;
export const MAX_SERIES = 8;
export const MAX_POINTS = 52;
export const MAX_REFERENCES = 3;

export interface ChartSeries {
  key: string;
  name: string;
  /** Lined up with `categories`; null is a gap (no bar, and a line breaks there). */
  values: (number | null)[];
  display: string[];
  /** The headline series: drawn in the accent colour. */
  emphasis: boolean;
}

export interface ChartReference {
  key: string;
  label: string;
  value: number;
  display: string;
}

export interface ChartPayload {
  version: number;
  id: string;
  title: string;
  kind: 'bar' | 'line';
  subtitle: string;
  x_label: string;
  y_label: string;
  categories: string[];
  series: ChartSeries[];
  y_max: number;
  references: ChartReference[];
  notes: string[];
  empty: string;
}

/** The drawing area, in SVG user units; the SVG scales to its container. */
export const VIEW = { width: 640, height: 260, left: 56, right: 16, top: 14, bottom: 30 } as const;
const PLOT_W = VIEW.width - VIEW.left - VIEW.right;
const PLOT_H = VIEW.height - VIEW.top - VIEW.bottom;
/** At most this many x labels, so they never overlap on a narrow card. */
export const MAX_X_LABELS = 8;
const Y_TICKS = 4;

/** Series colours in order; the emphasised series takes the accent instead. */
export const PALETTE = ['#c9a42c', '#69ccf0', '#1eff00', '#ff8000', '#a335ee', '#abd473', '#f58cba', '#fff569'];

export interface BarRect {
  x: number;
  y: number;
  width: number;
  height: number;
  colour: string;
  tip: string;
}

export interface LineShape {
  key: string;
  colour: string;
  emphasis: boolean;
  /** One SVG path per run of values without a gap. */
  paths: string[];
  /** Every point, for markers and tooltips. */
  points: { x: number; y: number; tip: string }[];
}

export interface Tick {
  y: number;
  label: string;
}

export interface Layout {
  bars: BarRect[];
  lines: LineShape[];
  references: (ChartReference & { y: number })[];
  yTicks: Tick[];
  xLabels: { x: number; label: string }[];
  legend: { name: string; colour: string }[];
}

/** 12345678 -> "12.3M", 4500 -> "4.5K", 950 -> "950": the analyzer's own compact numbers, for axis ticks. */
export function compact(n: number): string {
  for (const [size, suffix] of [
    [1e9, 'B'],
    [1e6, 'M'],
    [1e3, 'K']
  ] as const) {
    if (Math.abs(n) >= size) return `${(n / size).toFixed(1)}${suffix}`;
  }
  return Math.round(n).toLocaleString('en-GB');
}

/** True when the payload is a chart this hub can draw: its version, and within the limits. */
export function drawable(chart: ChartPayload | null | undefined): chart is ChartPayload {
  if (!chart || chart.version !== CHART_VERSION) return false;
  if (chart.categories.length > MAX_POINTS || chart.series.length > MAX_SERIES) return false;
  if ((chart.references ?? []).length > MAX_REFERENCES) return false;
  return chart.series.every((s) => s.values.length === chart.categories.length);
}

export function colours(series: readonly ChartSeries[], accent = 'var(--accent)'): string[] {
  let n = 0;
  return series.map((s) => (s.emphasis ? accent : PALETTE[n++ % PALETTE.length]));
}

function clampValue(v: number, max: number): number {
  return Math.max(0, Math.min(v, max));
}

export function layout(chart: ChartPayload, accent = 'var(--accent)'): Layout {
  const n = chart.categories.length;
  const max = chart.y_max > 0 ? chart.y_max : 1;
  const band = n ? PLOT_W / n : PLOT_W;
  const centre = (i: number) => VIEW.left + band * (i + 0.5);
  const yOf = (v: number) => VIEW.top + PLOT_H * (1 - clampValue(v, max) / max);
  const palette = colours(chart.series, accent);
  const tip = (s: ChartSeries, i: number) => `${s.name}, ${chart.categories[i]}: ${s.display[i] ?? ''}`;

  const bars: BarRect[] = [];
  const lines: LineShape[] = [];
  if (chart.kind === 'bar') {
    const groupWidth = band * 0.8;
    const width = chart.series.length ? groupWidth / chart.series.length : groupWidth;
    chart.series.forEach((s, j) => {
      s.values.forEach((v, i) => {
        if (v === null) return;
        const y = yOf(v);
        const x = centre(i) - groupWidth / 2 + j * width;
        bars.push({ x, y, width: Math.max(width - 1, 1), height: VIEW.top + PLOT_H - y, colour: palette[j], tip: tip(s, i) });
      });
    });
  } else {
    chart.series.forEach((s, j) => {
      const paths: string[] = [];
      const points: LineShape['points'] = [];
      let run: string[] = [];
      s.values.forEach((v, i) => {
        if (v === null) {
          if (run.length > 1) paths.push(run.join(' '));
          run = [];
          return;
        }
        const x = centre(i);
        const y = yOf(v);
        run.push(`${run.length ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`);
        points.push({ x, y, tip: tip(s, i) });
      });
      if (run.length > 1) paths.push(run.join(' '));
      lines.push({ key: s.key, colour: palette[j], emphasis: s.emphasis, paths, points });
    });
  }

  const step = Math.max(1, Math.ceil(n / MAX_X_LABELS));
  // Always label the newest category (the right-most); step back from it.
  const xLabels = chart.categories
    .map((label, i) => ({ x: centre(i), label, i }))
    .filter(({ i }) => (n - 1 - i) % step === 0)
    .map(({ x, label }) => ({ x, label }));
  const yTicks = Array.from({ length: Y_TICKS + 1 }, (_, k) => {
    const value = (chart.y_max * k) / Y_TICKS;
    return { y: yOf(value), label: compact(value) };
  });
  return {
    bars,
    lines,
    references: (chart.references ?? []).map((r) => ({ ...r, y: yOf(r.value) })),
    yTicks,
    xLabels,
    legend: chart.series.map((s, j) => ({ name: s.name, colour: palette[j] }))
  };
}
