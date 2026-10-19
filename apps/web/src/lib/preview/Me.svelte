<script lang="ts">
  import { base } from '$app/paths';
  import AwardsCard from '$lib/components/AwardsCard.svelte';
  import BadgesCard from '$lib/components/BadgesCard.svelte';
  import { titlesOf } from '$lib/awards';
  import { previewAwardsOf } from './awards-fake';
  import { previewBadges } from '$lib/mock/badges';
  import MemberToads from '$lib/components/MemberToads.svelte';
  import { getMe } from '$lib/me-context';
  import { me } from '$lib/mock/data';
  import { memberToads } from '$lib/toads';
  import TrendChart from './TrendChart.svelte';

  const MIN_RAIDS = 3;
  let selected = $state(me.characters[0].name);
  let character = $derived(me.characters.find((c) => c.name === selected)!);
  let history = $derived(me.history[selected] ?? []);
  let last = $derived(history.at(-1));
  const awards = previewAwardsOf(1);
  // The header's toads (rank, member, role badges, class and role), with the titles of the awards shown here.
  const signedIn = getMe();
  let facts = $derived({ ...signedIn(), titles: titlesOf(awards) });
  let toads = $derived(memberToads(facts));
</script>

<h1>Your performance <MemberToads {...facts} size={40} /></h1>

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
            <!-- The preview's Logs holds its own sample raids, not these, so each row opens the list. -->
            <td><a href="{base}/logs/">{r.zone}</a> <span class="muted">{r.date.slice(5)}</span></td>
            <td class="num">{r.mine}</td>
            <td class="num muted">{r.median}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </section>

  <div class="wide"><AwardsCard {awards} {toads} /></div>

  <div class="wide"><BadgesCard mine={previewBadges} /></div>

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
  .wide { grid-column: 1 / -1; }
</style>
