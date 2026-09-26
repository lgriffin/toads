<script lang="ts">
  import { base } from '$app/paths';
  import { me } from '$lib/mock/data';
  import TrendChart from './TrendChart.svelte';

  const MIN_RAIDS = 3;
  let selected = $state(me.characters[0].name);
  let character = $derived(me.characters.find((c) => c.name === selected)!);
  let history = $derived(me.history[selected] ?? []);
  let last = $derived(history.at(-1));
</script>

<h1>Your performance</h1>

<div class="chars">
  {#each me.characters as c}
    <button aria-pressed={c.name === selected} onclick={() => (selected = c.name)}>
      {c.name} <span class="muted">{c.spec}</span>
    </button>
  {/each}
</div>

<div class="grid">
  <section class="card">
    <h2>{character.metric} per raid vs {character.role.toLowerCase()} median</h2>
    {#if history.length < MIN_RAIDS}
      <p class="muted">
        Building your history. Trends show after {MIN_RAIDS} analysed raids; {character.name} has {history.length}.
      </p>
    {:else}
      <TrendChart points={history} />
    {/if}
    {#if last}
      {@const diff = Math.round(((last.mine - last.median) / last.median) * 100)}
      <p>
        Last raid ({last.zone}): <strong>{last.mine}</strong> {character.metric}, <span class:ok={diff >= 0} class:bad={diff < 0}
          >{diff >= 0 ? '+' : ''}{diff}%</span
        > against the guild median for {character.role.toLowerCase()}s.
      </p>
    {/if}
  </section>

  <section class="card">
    <h2>Raids</h2>
    <table>
      <thead><tr><th>Raid</th><th class="num">You</th><th class="num">Median</th></tr></thead>
      <tbody>
        {#each [...history].reverse() as r}
          <tr>
            <td><a href="{base}/raids/{r.raidId}/">{r.zone}</a> <span class="muted">{r.date.slice(5)}</span></td>
            <td class="num">{r.mine}</td>
            <td class="num muted">{r.median}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </section>

  <section class="card">
    <h2>Bank receipts</h2>
    <table>
      <thead><tr><th>Item</th><th class="num">Qty</th><th>Date</th></tr></thead>
      <tbody>
        {#each me.receipts as r}
          <tr>
            <td>{r.item}<br /><span class="muted small">{r.request}</span></td>
            <td class="num">{r.count}</td>
            <td>{r.date.slice(5)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </section>
</div>

<style>
  .chars { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem; }
  .chars button {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.4rem 0.75rem;
    font: inherit;
    cursor: pointer;
  }
  .chars button[aria-pressed='true'] { border-color: var(--accent); }
  .small { font-size: 0.8rem; }
</style>
