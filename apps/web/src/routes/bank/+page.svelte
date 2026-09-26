<script lang="ts">
  import { ageDays, ageLabel } from '$lib/format';
  import { MOCK_NOW, bankItems, bankSources } from '$lib/mock/data';

  const STALE_DAYS = 7;
  let selected = $state(bankSources[0].id);
  let source = $derived(bankSources.find((s) => s.id === selected)!);
  let items = $derived(bankItems.filter((i) => i.source === selected));
</script>

<h1>Guild bank</h1>

<div class="tabs" role="tablist">
  {#each bankSources as s}
    <button role="tab" aria-selected={s.id === selected} onclick={() => (selected = s.id)}>
      {s.raidDay} · {s.bankGuild}
    </button>
  {/each}
</div>

<section class="card">
  <p class="meta">
    Held by <strong>{source.character}</strong> · snapshot {ageLabel(source.snapshot, MOCK_NOW)} · uploaded by
    {source.uploader}
  </p>
  {#if ageDays(source.snapshot, MOCK_NOW) > STALE_DAYS}
    <p class="stale">This snapshot is over {STALE_DAYS} days old, so counts may be out of date.</p>
  {/if}
  <div class="scroll">
    <table>
      <thead><tr><th>Item</th><th>Tab</th><th class="num">Count</th><th></th></tr></thead>
      <tbody>
        {#each items as item}
          <tr>
            <td><span class="icon q-{item.quality}">{item.name[0]}</span><span class="q-{item.quality}">{item.name}</span></td>
            <td class="muted">{item.tab}</td>
            <td class="num">{item.count}</td>
            <td class="num"><button disabled title="Requests are disabled in the preview">Request</button></td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</section>

<style>
  .tabs { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem; }
  .tabs button, td button {
    background: var(--surface);
    color: var(--muted);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.4rem 0.75rem;
    font: inherit;
    cursor: pointer;
  }
  .tabs button[aria-selected='true'] { color: var(--text); border-color: var(--accent); }
  td button:disabled { cursor: not-allowed; opacity: 0.6; }
  .meta { margin-top: 0; }
  .stale { color: var(--warn); }
  .icon {
    display: inline-grid;
    place-items: center;
    width: 1.5rem;
    height: 1.5rem;
    margin-right: 0.5rem;
    border: 1px solid currentColor;
    border-radius: 4px;
    font-size: 0.75rem;
    vertical-align: middle;
  }
  .q-common { color: var(--text); }
  .q-uncommon { color: #1eff00; }
  .q-rare { color: #4f9dff; }
  .q-epic { color: #b56cff; }
</style>
