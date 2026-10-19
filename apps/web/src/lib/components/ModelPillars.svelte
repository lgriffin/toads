<script lang="ts">
  import { base } from '$app/paths';
  import { HOME_PILLARS, MODEL, type Pillar } from '$lib/landing';
  import { clearTrend, mainZone, series, type Point } from '$lib/pulse';
  import { clearTime, type RaidHeadline } from '$lib/sheets';
  import TrendBars from './TrendBars.svelte';

  // How a Toads raid night works. `compact` is the homepage's short version (HOME_PILLARS), a line each linking to the
  // full write-up of the six pillars on /how-we-raid. With a raid sheet trend, the full view also draws each pillar's recent numbers.
  let { compact = false, trend = [] }: { compact?: boolean; trend?: RaidHeadline[] } = $props();

  interface Chart {
    points: Point[];
    format: (v: number) => string;
    label: string;
    max?: number;
  }

  function chart(p: Pillar): Chart | null {
    switch (p.id) {
      case 'prep':
        return {
          points: series(trend, (r) => r.players_with_gear_issues),
          format: (v) => `${v} players`,
          label: 'Raiders with a missing enchant or gem, last four raids'
        };
      case 'flasks':
        return {
          points: series(trend, (r) => (r.consumables_avg === null ? null : r.consumables_avg * 100)),
          format: (v) => `${v.toFixed(1)}%`,
          label: 'Buff consumable uptime on bosses, last four raids',
          max: 100
        };
      case 'consumes':
        return {
          points: series(trend, (r) => r.potions),
          format: (v) => `${v}`,
          label: 'Potions used by the raid, last four raids'
        };
      case 'speed': {
        const zone = mainZone(trend);
        return zone
          ? { points: clearTrend(trend, zone).slice(-4), format: clearTime, label: `${zone} clear time, last four raids` }
          : null;
      }
      default:
        return null;
    }
  }
</script>

{#if compact}
  <ul class="pillars compact">
    {#each HOME_PILLARS as p (p.id)}
      <li class="card">
        <h3><a href="{base}/how-we-raid/#{p.id}">{p.title}</a></h3>
        <p class="muted">{p.summary}</p>
      </li>
    {/each}
  </ul>
{:else}
  <div class="pillars">
    {#each MODEL as p (p.id)}
      {@const c = trend.length ? chart(p) : null}
      <article class="card" id={p.id} aria-labelledby="{p.id}-h">
        <h2 id="{p.id}-h">{p.title}</h2>
        <dl>
          <dt>Our approach</dt>
          <dd>{p.approach}</dd>
          <dt>How we measure it</dt>
          <dd>{p.measure}</dd>
          <dt>What you see</dt>
          <dd>{p.youSee}</dd>
        </dl>
        {#if p.link}
          <p class="out">
            <a href={p.link.href} target="_blank" rel="noopener noreferrer"
              >{p.link.label}<span class="sr-only"> (opens in a new tab)</span></a
            >
          </p>
        {/if}
        {#if c && c.points.length}
          <TrendBars points={c.points} format={c.format} label={c.label} max={c.max ?? null} />
        {/if}
      </article>
    {/each}
  </div>
{/if}

<style>
  .pillars { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr)); }
  .compact { list-style: none; margin: 0; padding: 0; grid-template-columns: repeat(auto-fit, minmax(min(100%, 13rem), 1fr)); }
  .compact h3 { margin: 0 0 0.3rem; font-size: 1.05rem; }
  .compact p { margin: 0; font-size: 0.92rem; }
  article { display: grid; gap: 0.75rem; align-content: start; scroll-margin-top: 1rem; min-width: 0; }
  article h2 { margin: 0; }
  dl { margin: 0; display: grid; gap: 0.2rem; }
  dt { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-top: 0.4rem; }
  dt:first-child { margin-top: 0; }
  dd { margin: 0; }
  .out { margin: 0; }
</style>
