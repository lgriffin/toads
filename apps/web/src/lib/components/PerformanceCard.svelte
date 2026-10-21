<script lang="ts">
  import { base } from '$app/paths';
  import { dayMonth, shortDate } from '$lib/format';
  import { metricValue, rankLabel, rolePlural, signed, verdict, vsMedian, type MyPerformance } from '$lib/performance';

  // The member's main character in the last raid against the guild median for the same role (GET /api/me/performance).
  // The hub home leads with it: the one number only this guild's analysis can give a raider.
  let { mine }: { mine: MyPerformance } = $props();

  const entry = $derived(mine.entry);
  const diff = $derived(entry ? vsMedian(entry.value, entry.median) : 0);
  const peak = $derived(entry ? Math.max(...entry.recent.map((r) => Math.max(r.value, r.median)), 1) : 1);
  // The preview prerenders pages with trailing slashes.
  const slash = __PREVIEW__ ? '/' : '';
</script>

<section class="card perf" aria-labelledby="perf-h">
  {#if entry}
    <div class="lead">
      <h2 id="perf-h">
        <span class="who">{entry.name}</span>
        <span class:ok={diff > 0} class:bad={diff < 0}>{verdict(entry)}</span>
      </h2>
      <p>
        {metricValue(entry.value, entry.unit)} {entry.metric.toLowerCase()} across
        {mine.raid ? `${mine.raid.title}, ${shortDate(mine.raid.date)}` : 'the last raid'}. The median for
        {rolePlural(entry.role)} was {metricValue(entry.median, entry.unit)}; you placed {rankLabel(entry.rank, entry.of)}.
      </p>
      <p class="links">
        {#if mine.raid}<a href="{base}/logs/{mine.raid.report_id}{slash}">This raid's log</a> ·{/if}
        <a href="{base}/me{slash}">All your raids on Me</a>
      </p>
    </div>
    {#if entry.recent.length > 1}
      <div class="trend-box">
        <h3 class="muted">Your last {entry.recent.length} raids as {entry.role}</h3>
        <ul class="trend" aria-label="{entry.name}'s last {entry.recent.length} raids against the median">
          {#each entry.recent as r, i (i)}
            {@const d = vsMedian(r.value, r.median)}
            <li>
              <span class="muted date">{dayMonth(r.date)}</span>
              <span class="bar" aria-hidden="true">
                <span class="fill" class:bad={d < 0} style="width: {(r.value / peak) * 100}%"></span>
                <span class="median" style="left: {(r.median / peak) * 100}%"></span>
              </span>
              <span class="num">{signed(d)}<span class="sr-only"> against the median</span></span>
            </li>
          {/each}
        </ul>
        <p class="muted small key"><span class="tick" aria-hidden="true"></span> marks the median</p>
      </div>
    {/if}
  {:else}
    <div class="lead">
      <h2 id="perf-h">Your last raid</h2>
      {#if !mine.generated_at}
        <p class="muted">Shows once the worker has analysed the guild’s raids.</p>
      {:else if mine.looked_for.length}
        <p class="muted">
          {mine.looked_for.join(', ')} {mine.looked_for.length === 1 ? 'was' : 'were'} not in the last raid.
        </p>
      {:else}
        <p class="muted">Claim your characters to see how each raid went for you against the median for your role.</p>
      {/if}
      <p class="links"><a href="{base}/me/claim{slash}">Claim your characters</a></p>
    </div>
  {/if}
</section>

<style>
  .perf {
    display: grid;
    gap: 1rem 2rem;
    grid-template-columns: minmax(0, 1fr);
    border-color: color-mix(in srgb, var(--bronze) 45%, var(--line));
  }
  @media (min-width: 52rem) {
    .perf:has(.trend-box) { grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); align-items: center; }
  }
  .lead { display: grid; gap: 0.5rem; }
  .lead p { margin: 0; max-width: 60ch; }
  h2 {
    margin: 0;
    font-family: 'Cinzel', Georgia, serif;
    font-size: clamp(1.35rem, 1.1rem + 1vw, 1.8rem);
    line-height: 1.25;
    color: var(--bronze-hi);
    text-wrap: balance;
  }
  h2 .who { color: var(--cream); }
  h2 .ok { color: var(--accent); }
  h2 .bad { color: var(--bad-text); }
  h3 { font-size: 0.85rem; font-weight: 500; margin: 0 0 0.5rem; }
  .links { font-size: 0.95rem; }
  .trend { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.35rem; }
  .trend li { display: grid; grid-template-columns: 3.75rem minmax(0, 1fr) 3.25rem; gap: 0.5rem; align-items: center; }
  .bar { position: relative; height: 0.6rem; background: var(--line); border-radius: 3px; }
  .fill { position: absolute; inset: 0 auto 0 0; background: var(--accent); border-radius: 3px; }
  .fill.bad { background: var(--bad); }
  .median, .tick { position: absolute; top: -3px; bottom: -3px; width: 2px; background: var(--cream); }
  .date { white-space: nowrap; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .key { margin: 0.5rem 0 0; display: flex; align-items: center; gap: 0.4rem; }
  .tick { position: relative; display: inline-block; top: 0; bottom: 0; height: 0.9rem; }
  .small { font-size: 0.85rem; }
</style>
