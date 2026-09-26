<script lang="ts">
  import { base } from '$app/paths';
  import { shortDate } from '$lib/format';
  import { MOCK_NOW, raids } from '$lib/mock/data';
  import { ALL, filterRaids } from '$lib/raids';

  const zones = [...new Set(raids.map((r) => r.zone))];
  let zone = $state(ALL);
  let raidDay = $state(ALL);
  let size = $state(ALL);
  let lookbackDays = $state(30);
  let shown = $derived(filterRaids(raids, { zone, raidDay, size, lookbackDays }, MOCK_NOW));
</script>

<h1>Raids &amp; Logs</h1>

<form class="filters" onsubmit={(e) => e.preventDefault()}>
  <label>Zone
    <select bind:value={zone}>
      <option value={ALL}>All zones</option>
      {#each zones as z}<option>{z}</option>{/each}
    </select>
  </label>
  <label>Raid day
    <select bind:value={raidDay}>
      <option value={ALL}>Both</option>
      <option>Wednesday</option>
      <option>Sunday</option>
    </select>
  </label>
  <label>Size
    <select bind:value={size}>
      <option value={ALL}>Any</option>
      <option value="10">10</option>
      <option value="25">25</option>
    </select>
  </label>
  <label>Lookback
    <select bind:value={lookbackDays}>
      <option value={7}>7 days</option>
      <option value={14}>14 days</option>
      <option value={30}>30 days</option>
    </select>
  </label>
</form>

<div class="card scroll">
  <table>
    <thead>
      <tr><th>Date</th><th>Zone</th><th>Day</th><th class="num">Size</th><th class="num">Bosses</th><th class="num">Deaths</th></tr>
    </thead>
    <tbody>
      {#each shown as raid}
        <tr>
          <td>{shortDate(raid.date)}</td>
          <td><a href="{base}/raids/{raid.id}/">{raid.zone}</a></td>
          <td>{raid.raidDay}</td>
          <td class="num">{raid.size}</td>
          <td class="num">{raid.bosses.filter((b) => b.killed).length}/{raid.bosses.length}</td>
          <td class="num">{raid.deaths}</td>
        </tr>
      {:else}
        <tr><td colspan="6" class="muted">No raids match these filters.</td></tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .filters { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 1rem; }
  label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: var(--muted); }
  select { background: var(--surface); color: var(--text); border: 1px solid var(--line); border-radius: 6px; padding: 0.35rem; }
</style>
