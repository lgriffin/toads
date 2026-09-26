<script lang="ts">
  import type { MeRaid } from '$lib/mock/data';

  let { points }: { points: MeRaid[] } = $props();

  const W = 360;
  const H = 180;
  const PAD = { l: 40, r: 10, t: 10, b: 24 };

  let values = $derived(points.flatMap((p) => [p.mine, p.median]));
  let lo = $derived(Math.floor((Math.min(...values) * 0.95) / 50) * 50);
  let hi = $derived(Math.ceil((Math.max(...values) * 1.05) / 50) * 50);
  let x = $derived((i: number) => PAD.l + (i * (W - PAD.l - PAD.r)) / Math.max(1, points.length - 1));
  let y = $derived((v: number) => PAD.t + ((hi - v) * (H - PAD.t - PAD.b)) / (hi - lo));
  let line = $derived((key: 'mine' | 'median') => points.map((p, i) => `${x(i)},${y(p[key])}`).join(' '));
</script>

<svg viewBox="0 0 {W} {H}" role="img" aria-label="Your metric per raid against the guild median">
  {#each [lo, (lo + hi) / 2, hi] as t}
    <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} class="grid" />
    <text x={PAD.l - 6} y={y(t) + 4} text-anchor="end">{Math.round(t)}</text>
  {/each}
  {#each points as p, i}
    <text x={x(i)} y={H - 6} text-anchor="middle">{p.zone}</text>
  {/each}
  <polyline points={line('median')} class="median" />
  <polyline points={line('mine')} class="mine" />
  {#each points as p, i}
    <circle cx={x(i)} cy={y(p.mine)} r="3.5" />
  {/each}
</svg>
<p class="legend"><span class="k mine"></span>You <span class="k median"></span>Guild median</p>

<style>
  svg { width: 100%; height: auto; display: block; }
  text { fill: var(--muted); font-size: 10px; }
  .grid { stroke: var(--line); }
  polyline { fill: none; stroke-width: 2; }
  polyline.mine { stroke: var(--accent); }
  polyline.median { stroke: var(--muted); stroke-dasharray: 4 4; }
  circle { fill: var(--accent); }
  .legend { font-size: 0.8rem; color: var(--muted); display: flex; align-items: center; gap: 0.4rem; }
  .k { display: inline-block; width: 1rem; height: 2px; }
  .k.mine { background: var(--accent); }
  .k.median { background: var(--muted); margin-left: 0.75rem; }
</style>
