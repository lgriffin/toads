<script lang="ts">
  import { base } from '$app/paths';
  import { MODEL, type Pillar } from '$lib/landing';
  import { clearTrend, mainZone, series, type Point } from '$lib/pulse';
  import { clearTime, type RaidHeadline } from '$lib/sheets';
  import TrendBars from './TrendBars.svelte';

  // The six pillars of how a Toads raid night works. `compact` is the homepage: a line each, linking to the full
  // write-up on /how-we-raid. With a raid sheet trend, the full view also draws each pillar's recent numbers.
  let { compact = false, trend = [] }: { compact?: boolean; trend?: RaidHeadline[] } = $props();

  const TIERS = ['Uncommon', 'Rare', 'Epic', 'Legendary'] as const;

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
    {#each MODEL as p (p.id)}
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
        {#if p.id === 'badges'}
          <p class="tiers" aria-label="Badge tiers">
            {#each TIERS as t}<span class="tier {t.toLowerCase()}">{t}</span>{/each}
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
  .compact { list-style: none; margin: 0; padding: 0; }
  .compact h3 { margin: 0 0 0.3rem; font-size: 1.05rem; }
  .compact p { margin: 0; font-size: 0.92rem; }
  article { display: grid; gap: 0.75rem; align-content: start; scroll-margin-top: 1rem; min-width: 0; }
  article h2 { margin: 0; }
  dl { margin: 0; display: grid; gap: 0.2rem; }
  dt { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-top: 0.4rem; }
  dt:first-child { margin-top: 0; }
  dd { margin: 0; }
  .tiers { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0; }
  .tier { border: 1.5px solid currentColor; border-radius: 6px; padding: 0.1rem 0.5rem; font-size: 0.82rem; font-weight: 600; }
  /* The badge guide's quality colours, lightened where needed to stay readable on the dark theme (see badges.ts). */
  .uncommon { color: #1eff00; }
  .rare { color: #5aa9ff; }
  .epic { color: #c58af9; }
  .legendary { color: #ff8000; }
</style>
