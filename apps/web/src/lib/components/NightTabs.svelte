<script lang="ts">
  import { base } from '$app/paths';
  import type { LogNight } from '$lib/logs';
  import { raidNight } from '$lib/nights';

  // Picks the raid night the Logs page shows, or every raid (null). One is always picked, like tabs.
  let {
    nights,
    value,
    onpick
  }: { nights: readonly LogNight[]; value: string | null; onpick: (night: string | null) => void } = $props();

  const toad = (n: LogNight) => raidNight(n.id)?.toad ?? raidNight(n.name)?.toad;
</script>

<div class="nights" role="group" aria-label="Raid night">
  {#each nights as n (n.id)}
    {@const art = toad(n)}
    <button type="button" aria-pressed={value === n.id} onclick={() => onpick(n.id)}>
      {#if art}<img src="{base}/logos/{art}.svg" alt="" width="28" height="28" />{/if}
      {n.name}
    </button>
  {/each}
  <button type="button" aria-pressed={value === null} onclick={() => onpick(null)}>Every raid</button>
</div>

<style>
  .nights { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  button {
    font: inherit;
    font-family: 'Cinzel', Georgia, serif;
    font-size: 1.05rem;
    letter-spacing: 0.05em;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    min-height: 2.75rem;
    padding: 0.35rem 1.1rem 0.35rem 0.6rem;
    border: 1px solid var(--bronze);
    border-radius: 999px;
    background: color-mix(in srgb, var(--ink) 45%, transparent);
    color: var(--cream);
    cursor: pointer;
  }
  button:last-child { padding-left: 1.1rem; }
  img { display: block; }
  button[aria-pressed='true'] { background: var(--bronze); color: var(--on-bronze); font-weight: 700; }
  button:hover:not([aria-pressed='true']) { background: color-mix(in srgb, var(--teal) 18%, transparent); }
  button:focus-visible { outline: 2px solid var(--bronze-hi); outline-offset: 2px; }
</style>
