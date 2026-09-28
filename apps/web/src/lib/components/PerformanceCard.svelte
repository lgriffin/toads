<script lang="ts">
  import { base } from '$app/paths';
  import { metricValue, rankLabel, rolePlural, signed, vsMedian, type MyPerformance } from '$lib/performance';

  // The member's main character in the last raid against the guild median for the same role (GET /api/me/performance).
  let { mine }: { mine: MyPerformance } = $props();

  const entry = $derived(mine.entry);
  const diff = $derived(entry ? vsMedian(entry.value, entry.median) : 0);
  const peak = $derived(entry ? Math.max(...entry.recent.map((r) => Math.max(r.value, r.median)), 1) : 1);
</script>

<section class="card" aria-labelledby="perf-h">
  <h2 id="perf-h">Your performance</h2>
  {#if entry}
    <p class="big">{metricValue(entry.value, entry.unit)} {entry.metric.toLowerCase()}</p>
    <p>
      {entry.name}{mine.raid ? ` in ${mine.raid.title}` : ''}:
      <span class:ok={diff >= 0} class:bad={diff < 0}>{signed(diff)}</span>
      against the guild median for {rolePlural(entry.role)} ({metricValue(entry.median, entry.unit)}),
      {rankLabel(entry.rank, entry.of)}.
    </p>
    {#if entry.recent.length > 1}
      <ul class="trend" aria-label="{entry.name}'s last {entry.recent.length} raids against the median">
        {#each entry.recent as r, i (i)}
          {@const d = vsMedian(r.value, r.median)}
          <li>
            <span class="muted date">{r.date.slice(5)}</span>
            <span class="bar" aria-hidden="true">
              <span class="fill" class:bad={d < 0} style="width: {(r.value / peak) * 100}%"></span>
              <span class="median" style="left: {(r.median / peak) * 100}%"></span>
            </span>
            <span class="num">{signed(d)}</span>
          </li>
        {/each}
      </ul>
    {/if}
  {:else if !mine.generated_at}
    <p class="muted">Shows once the worker has analysed the guild’s raids.</p>
  {:else if mine.looked_for.length}
    <p class="muted">{mine.looked_for.join(', ')} {mine.looked_for.length === 1 ? 'was' : 'were'} not in the last raid.</p>
  {:else}
    <p class="muted">Claim your characters to see your numbers here.</p>
  {/if}
  <!-- The preview prerenders pages with trailing slashes. -->
  <a href="{base}/me/claim{__PREVIEW__ ? '/' : ''}">Claim your characters</a>
</section>

<style>
  .big { font-size: 1.3rem; margin: 0; }
  .trend { list-style: none; padding: 0; margin: 0.5rem 0; display: grid; gap: 0.25rem; }
  .trend li { display: grid; grid-template-columns: 3rem minmax(0, 1fr) 3.5rem; gap: 0.5rem; align-items: center; }
  .bar { position: relative; height: 0.6rem; background: var(--line); border-radius: 3px; }
  .fill { position: absolute; inset: 0 auto 0 0; background: var(--accent); border-radius: 3px; }
  .fill.bad { background: var(--bad); }
  .median { position: absolute; top: -2px; bottom: -2px; width: 2px; background: currentColor; }
  .num { text-align: right; }
</style>
