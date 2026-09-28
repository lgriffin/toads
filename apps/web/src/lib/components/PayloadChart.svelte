<script lang="ts">
  import { VIEW, drawable, layout, type ChartPayload } from '$lib/charts';

  // Draws one analyzer chart payload (guides/charts.md). Labels come from logs, so they are only ever text nodes,
  // never {@html}. A table of the same numbers follows for screen readers.
  let { chart }: { chart: ChartPayload | null } = $props();

  const ok = $derived(drawable(chart));
  const l = $derived(ok && chart ? layout(chart) : null);
  const plotRight = VIEW.width - VIEW.right;
  const plotBottom = VIEW.height - VIEW.bottom;
</script>

{#if chart?.empty}
  <p class="muted">{chart.empty}</p>
{:else if !chart || !ok || !l}
  <p class="muted">This chart could not be drawn.</p>
{:else}
  <figure class="chart">
    <svg viewBox="0 0 {VIEW.width} {VIEW.height}" role="img" aria-label="{chart.title}: {chart.y_label} by {chart.x_label}">
      {#each l.yTicks as t, i (i)}
        <line class="grid" x1={VIEW.left} x2={plotRight} y1={t.y} y2={t.y} />
        <text class="tick" x={VIEW.left - 6} y={t.y} text-anchor="end" dominant-baseline="middle">{t.label}</text>
      {/each}
      {#each l.xLabels as x, i (i)}
        <text class="tick" x={x.x} y={plotBottom + 18} text-anchor="middle">{x.label}</text>
      {/each}
      {#each l.bars as b, i (i)}
        <rect x={b.x} y={b.y} width={b.width} height={b.height} rx="2" fill={b.colour}><title>{b.tip}</title></rect>
      {/each}
      {#each l.lines as line (line.key)}
        {#each line.paths as d, i (i)}
          <path {d} fill="none" stroke={line.colour} stroke-width={line.emphasis ? 3 : 2} stroke-linejoin="round" />
        {/each}
        {#each line.points as p, i (i)}
          <circle cx={p.x} cy={p.y} r="3.5" fill={line.colour}><title>{p.tip}</title></circle>
        {/each}
      {/each}
      {#each l.references as r, i (i)}
        <line class="ref" x1={VIEW.left} x2={plotRight} y1={r.y} y2={r.y} />
        <text class="ref-label" x={plotRight} y={r.y - 4} text-anchor="end">{r.label} {r.display}</text>
      {/each}
      <line class="axis" x1={VIEW.left} x2={plotRight} y1={plotBottom} y2={plotBottom} />
    </svg>
    {#if l.legend.length > 1}
      <ul class="legend">
        {#each l.legend as e, i (i)}
          <li><span class="swatch" style="background: {e.colour}"></span>{e.name}</li>
        {/each}
      </ul>
    {/if}
    {#if chart.notes?.length}
      <figcaption>
        {#each chart.notes as note, i (i)}<p class="muted">{note}</p>{/each}
      </figcaption>
    {/if}
    <table class="sr-only">
      <caption>{chart.title}</caption>
      <thead>
        <tr>
          <th scope="col">{chart.x_label}</th>
          {#each chart.series as s (s.key)}<th scope="col">{s.name}</th>{/each}
        </tr>
      </thead>
      <tbody>
        {#each chart.categories as c, i (i)}
          <tr>
            <th scope="row">{c}</th>
            {#each chart.series as s (s.key)}<td>{s.display[i]}</td>{/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </figure>
{/if}

<style>
  .chart { margin: 0; }
  svg { display: block; width: 100%; height: auto; overflow: visible; }
  .grid { stroke: var(--line); stroke-width: 1; }
  .axis { stroke: var(--muted, currentColor); stroke-width: 1; }
  .tick { fill: var(--muted, currentColor); font-size: 11px; font-variant-numeric: tabular-nums; }
  .ref { stroke: var(--text, currentColor); stroke-width: 1.5; stroke-dasharray: 6 4; opacity: 0.8; }
  .ref-label { fill: var(--text, currentColor); font-size: 11px; }
  .legend { display: flex; flex-wrap: wrap; gap: 0.35rem 1rem; list-style: none; margin: 0.5rem 0 0; padding: 0; font-size: 0.85rem; }
  .swatch { display: inline-block; width: 0.75rem; height: 0.75rem; border-radius: 2px; margin-right: 0.35rem; vertical-align: -1px; }
  figcaption p { margin: 0.35rem 0 0; font-size: 0.9rem; }
  .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
</style>
