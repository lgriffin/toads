<script lang="ts">
  import { shortDate } from '$lib/format';
  import {
    change,
    clearTime,
    clearTimes,
    count,
    gearLabel,
    newestFirst,
    percent,
    points,
    previousRaid,
    reportUrl,
    type Change,
    type RaidHeadline
  } from '$lib/sheets';

  // Sheet text (titles, zones, names) is untrusted: only ever interpolated as text, never with {@html}.
  let { raids, id = 'raid-totals' }: { raids: RaidHeadline[]; id?: string } = $props();

  const sorted = $derived(newestFirst(raids));
  const latest = $derived(sorted[0] ?? null);
  const prev = $derived(latest ? previousRaid(sorted, latest) : null);
  const link = $derived(reportUrl(latest?.report_code));

  interface Stat {
    label: string;
    value: string;
    change: Change | null;
  }

  const stats = $derived.by((): Stat[] => {
    if (!latest) return [];
    const up = { lowerIsBetter: false };
    return [
      { label: 'Gear issues', value: gearLabel(latest), change: change(latest.gear_issues, prev?.gear_issues) },
      { label: 'Potions', value: count(latest.potions), change: change(latest.potions, prev?.potions, up) },
      { label: 'Drums', value: count(latest.drums), change: change(latest.drums, prev?.drums, up) },
      { label: 'Interrupts', value: count(latest.interrupts), change: change(latest.interrupts, prev?.interrupts, up) },
      { label: 'Deaths', value: count(latest.deaths), change: change(latest.deaths, prev?.deaths) },
      {
        label: 'Avoidable damage',
        value: count(latest.avoidable_damage),
        change: change(latest.avoidable_damage, prev?.avoidable_damage)
      }
    ];
  });
  const consumeChange = $derived(
    latest ? change(latest.consumables_avg, prev?.consumables_avg, { lowerIsBetter: false, format: points }) : null
  );
</script>

{#snippet delta(c: Change | null)}
  {#if c}
    <span class="delta" class:ok={c.tone === 'better'} class:bad={c.tone === 'worse'}>
      {c.label}<span class="sr-only"> on the previous raid</span>
    </span>
  {/if}
{/snippet}

<section class="card totals" aria-labelledby="{id}-h">
  <h2 id="{id}-h">Raid totals</h2>
  {#if !latest}
    <p class="muted">
      No raid sheets yet. Totals appear here once the CBA and RPB sheets for a raid have been imported.
    </p>
  {:else}
    <div class="head">
      <div>
        <p class="big">{latest.zone ?? latest.title ?? 'Raid'}</p>
        <p class="muted">
          <time datetime={latest.raid_date}>{shortDate(latest.raid_date)}</time>
          {#if latest.characters !== null}· {latest.characters} characters{/if}
          {#if link}
            · <a href={link} target="_blank" rel="noopener noreferrer"
              >Warcraft Logs report<span class="sr-only"> (opens in a new tab)</span></a
            >
          {/if}
        </p>
      </div>
      {#if latest.log_valid === false}
        <span class="pill warn" title="The log did not meet the sheet's kill requirements">Log not valid</span>
      {/if}
    </div>

    <dl class="clears">
      {#each latest.clear_times as t}
        <div>
          <dt>{t.zone} clear</dt>
          <dd class="time">{clearTime(t.seconds)}</dd>
        </div>
      {:else}
        <div>
          <dt>Clear time</dt>
          <dd class="time">{clearTime(null)}</dd>
        </div>
      {/each}
    </dl>

    <div class="consumes">
      <p>
        <span class="label">Consumables</span>
        <span class="value">{percent(latest.consumables_avg)}</span>
        <span class="muted">average uptime on bosses</span>
        {@render delta(consumeChange)}
      </p>
      {#if latest.consumables_avg !== null}
        {#if latest.low_consumables.length}
          <p class="small">
            <span class="muted">Under 80%:</span>
            {latest.low_consumables.join(', ')}
          </p>
        {:else}
          <p class="small muted">Everyone at 80% or above.</p>
        {/if}
      {/if}
    </div>

    <dl class="stats">
      {#each stats as s}
        <div>
          <dt>{s.label}</dt>
          <dd><span class="value">{s.value}</span> {@render delta(s.change)}</dd>
        </div>
      {/each}
    </dl>
    {#if prev}
      <p class="small muted">Changes compare with {shortDate(prev.raid_date)}.</p>
    {/if}

    <h3 id="{id}-recent">Recent raids</h3>
    <div class="scroll">
      <table aria-labelledby="{id}-recent">
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Zone</th>
            <th scope="col">Clear times</th>
            <th scope="col" class="num">Consumables</th>
            <th scope="col" class="num">Gear issues</th>
            <th scope="col" class="num">Deaths</th>
          </tr>
        </thead>
        <tbody>
          {#each sorted as r (`${r.raid_day}:${r.raid_date}`)}
            <tr>
              <th scope="row" class="date"><time datetime={r.raid_date}>{shortDate(r.raid_date)}</time></th>
              <td>{r.zone ?? '—'}{#if r.log_valid === false}<span class="warn" title="Log not valid"> *</span><span class="sr-only"> (log not valid)</span>{/if}</td>
              <td class="times">{clearTimes(r.clear_times)}</td>
              <td class="num">{percent(r.consumables_avg)}</td>
              <td class="num">{count(r.gear_issues)}</td>
              <td class="num">{count(r.deaths)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>

<style>
  .totals { min-width: 0; }
  .head { display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; justify-content: space-between; align-items: flex-start; }
  .head p { margin: 0; }
  .big { font-size: 1.3rem; }
  dl { margin: 0.75rem 0; display: grid; gap: 0.5rem 1rem; grid-template-columns: repeat(auto-fit, minmax(8.5rem, 1fr)); }
  dt { color: var(--muted); font-size: 0.8rem; }
  dd { margin: 0; font-variant-numeric: tabular-nums; }
  .time { font-size: 1.3rem; }
  .value { font-size: 1.05rem; }
  .label { color: var(--muted); font-size: 0.8rem; display: block; }
  .consumes p { margin: 0 0 0.25rem; }
  .delta { font-size: 0.8rem; color: var(--muted); white-space: nowrap; }
  .delta.ok { color: var(--accent); }
  .delta.bad { color: var(--bad); }
  .small { font-size: 0.8rem; }
  h3 { font-size: 0.95rem; margin: 1rem 0 0.5rem; }
  th.date { color: var(--text); font-weight: 400; white-space: nowrap; }
  .times { white-space: nowrap; }
</style>
