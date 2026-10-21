<script lang="ts">
  import { base } from '$app/paths';
  import { compactNumber, durationLabel } from '$lib/reference';
  import {
    bossHistory,
    filterRaids,
    logsError,
    raidDateLabel,
    raidsPerWeekday,
    weekdayName,
    WEEKDAYS,
    zonesOf,
    type LogsBackend,
    type LogsOverview,
    type RaidRow
  } from '$lib/logs';
  import WeekdayChips from './WeekdayChips.svelte';

  // The raid list and the boss history, both cut to the weekdays picked above them (the page starts them on the
  // picked raid night). Who sees per-player numbers is the API's call (docs/logs.md); this only shows what came back.
  let { backend, weekdays = $bindable([]) }: { backend: LogsBackend; weekdays?: number[] } = $props();

  let overview = $state<LogsOverview | null>(null);
  let error = $state('');
  let zone = $state('');
  let query = $state('');

  $effect(() => {
    backend.overview().then(
      (o) => (overview = o),
      (e) => (error = logsError(e))
    );
  });

  const rows = $derived(overview?.raids ?? []);
  const shown = $derived(filterRaids(rows, { weekdays, zone, query }));
  const bosses = $derived(bossHistory(overview?.bosses ?? [], weekdays));
  const counts = $derived(raidsPerWeekday(rows));
  const daysLabel = $derived(
    weekdays.length ? weekdays.map((d) => WEEKDAYS[d].name).join(', ') : 'every day'
  );

  function href(r: RaidRow): string {
    const day = r.day ? `?day=${encodeURIComponent(r.day)}` : '';
    return `${base}/logs/${encodeURIComponent(r.summary.report_id)}/${day}`;
  }
</script>

{#if error}
  <p class="card bad" role="alert">{error}</p>
{:else if !overview}
  <p class="muted" role="status">Loading…</p>
{:else if !rows.length}
  <section class="card">
    <h2>No raids yet</h2>
    <p class="muted">Raids appear here once the hub has synced them from Warcraft Logs and analysed them.</p>
  </section>
{:else}
  <section class="filters card" aria-label="Filters">
    <WeekdayChips bind:value={weekdays} {counts} />
    <div class="row">
      <label class="field">Zone
        <select bind:value={zone}>
          <option value="">Every zone</option>
          {#each zonesOf(rows) as z (z)}<option>{z}</option>{/each}
        </select>
      </label>
      <label class="field grow">Search
        <input type="search" bind:value={query} placeholder="Raid title or zone" />
      </label>
    </div>
  </section>

  <section class="card" aria-labelledby="raids-h">
    <h2 id="raids-h">Raids</h2>
    <p class="muted" aria-live="polite">{shown.length} of {rows.length} raids, {daysLabel}.</p>
    <div class="scroll">
      <table>
        <thead>
          <tr>
            <th scope="col">Date</th><th scope="col">Day</th><th scope="col">Raid</th><th scope="col">Zone</th>
            <th scope="col" class="num">Size</th><th scope="col">Analysis</th>
          </tr>
        </thead>
        <tbody>
          {#each shown as r (r.summary.report_id)}
            <tr>
              <td class="nowrap">{raidDateLabel(r.summary)}</td>
              <td>{weekdayName(r.summary.weekday)}</td>
              <td>
                {#if r.analysed}<a href={href(r)}>{r.summary.title}</a>{:else}{r.summary.title}{/if}
              </td>
              <td>{r.summary.zone}</td>
              <td class="num">{r.summary.size}</td>
              <td>
                {#if !r.analysed}<span class="muted">Being analysed</span>
                {:else if r.full}<span class="pill full">Full</span>
                {:else}<span class="pill">Overview</span>{/if}
              </td>
            </tr>
          {:else}
            <tr><td colspan="6" class="muted">No raids match these filters.</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="card" aria-labelledby="bosses-h">
    <h2 id="bosses-h">Boss history</h2>
    <p class="muted">Every kill on {daysLabel}, averaged. Open a boss for each raider's damage and healing per kill.</p>
    {#if bosses.length}
      <ul class="bosses">
        {#each bosses as b (b.encounter_id)}
          <li>
            <details>
              <summary>
                <span class="boss">{b.name}</span>
                <span class="stat"><span class="k">{b.kills}</span> {b.kills === 1 ? 'kill' : 'kills'}</span>
                <span class="stat"><span class="k">{durationLabel(b.duration_ms)}</span> avg</span>
                <span class="stat"><span class="k">{compactNumber(b.dps)}</span> raid DPS</span>
                <span class="stat"><span class="k">{compactNumber(b.hps)}</span> raid HPS</span>
              </summary>
              {#if b.players}
                {#if b.partial}
                  <p class="muted small">Only the nights you run as an officer are counted below.</p>
                {/if}
                <div class="scroll">
                  <table>
                    <caption class="sr-only">{b.name}: each raider per kill</caption>
                    <thead>
                      <tr>
                        <th scope="col">Raider</th><th scope="col">Class</th><th scope="col">Role</th><th scope="col" class="num">Kills</th>
                        <th scope="col" class="num">Damage per kill</th><th scope="col" class="num">Healing per kill</th>
                      </tr>
                    </thead>
                    <tbody>
                      {#each b.players as p (`${p.name}|${p.role}`)}
                        <tr>
                          <th scope="row">{p.name}</th>
                          <td>{p.player_class}</td>
                          <td>{p.role}</td>
                          <td class="num">{p.kills}</td>
                          <td class="num">{compactNumber(p.damage_per_kill)}</td>
                          <td class="num">{compactNumber(p.healing_per_kill)}</td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              {:else}
                <p class="muted small">Each raider's numbers are for that night's officers.</p>
              {/if}
            </details>
          </li>
        {/each}
      </ul>
    {:else}
      <p class="muted">No boss kills on these days yet.</p>
    {/if}
  </section>
{/if}

<style>
  section + section { margin-top: 1rem; }
  .filters { display: grid; gap: 0.9rem; }
  .row { display: flex; flex-wrap: wrap; gap: 0.75rem 1rem; }
  .grow { flex: 1 1 14rem; }
  select, input {
    font: inherit;
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.45rem 0.6rem;
    min-height: 2.5rem;
  }
  h2 { margin: 0 0 0.35rem; }
  .nowrap { white-space: nowrap; }
  .full { background: var(--bronze); color: var(--on-bronze); }
  .bosses { list-style: none; margin: 0.5rem 0 0; padding: 0; }
  .bosses li { border-top: 1px solid var(--line); }
  summary {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.25rem 1.25rem;
    padding: 0.65rem 0.25rem;
    cursor: pointer;
  }
  summary:focus-visible { outline: 2px solid var(--bronze-hi); outline-offset: 2px; }
  .boss { font-weight: 700; flex: 1 1 14rem; }
  .stat { color: var(--muted); font-variant-numeric: tabular-nums; }
  .k { color: var(--text); font-weight: 700; }
  .small { font-size: 0.9rem; }
  details[open] { padding-bottom: 0.75rem; }
</style>
