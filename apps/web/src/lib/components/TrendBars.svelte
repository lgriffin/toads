<script lang="ts">
  import type { Point } from '$lib/pulse';

  // A few points as labelled horizontal bars, oldest first, the newest one highlighted. Bars are drawn against the
  // largest value; `label` says what the bars are, for screen readers and as the caption.
  let {
    points,
    format,
    label,
    max = null
  }: { points: Point[]; format: (value: number) => string; label: string; max?: number | null } = $props();

  const top = $derived(max ?? Math.max(...points.map((p) => p.value), 0));
  const day = (iso: string) =>
    new Date(`${iso}T12:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });
</script>

{#if points.length}
  <figure class="trend">
    <ul aria-label={label}>
      {#each points as p, i (p.date)}
        <li class:last={i === points.length - 1}>
          <span class="when">{day(p.date)}</span>
          <span class="track" aria-hidden="true"><span style="width: {top ? (p.value / top) * 100 : 0}%"></span></span>
          <span class="val">{format(p.value)}</span>
        </li>
      {/each}
    </ul>
    <figcaption class="muted">{label}</figcaption>
  </figure>
{/if}

<style>
  .trend { margin: 0; display: grid; gap: 0.4rem; }
  ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.3rem; }
  li { display: grid; grid-template-columns: 3.6rem minmax(0, 1fr) 5.4rem; align-items: center; gap: 0.5rem; font-size: 0.85rem; }
  .when { color: var(--muted); }
  .val { text-align: right; font-variant-numeric: tabular-nums; }
  .track { display: block; height: 0.45rem; border-radius: 999px; background: var(--line); overflow: hidden; }
  .track span { display: block; height: 100%; background: var(--muted); }
  .last .track span { background: var(--accent); }
  .last .val { font-weight: 600; }
  figcaption { font-size: 0.8rem; }
</style>
