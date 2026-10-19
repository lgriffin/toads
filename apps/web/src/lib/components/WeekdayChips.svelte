<script lang="ts">
  import { WEEKDAYS, toggleWeekday } from '$lib/logs';

  // Picks the weekdays the Logs page shows, any mix of them; none picked shows every day. Each chip shows how many
  // raids fell on that weekday.
  let { value = $bindable(), counts }: { value: number[]; counts: number[] } = $props();
</script>

<div class="chips" role="group" aria-label="Raid days">
  <button type="button" aria-pressed={value.length === 0} onclick={() => (value = [])}>Every day</button>
  {#each WEEKDAYS as w (w.day)}
    <button type="button" aria-pressed={value.includes(w.day)} onclick={() => (value = toggleWeekday(value, w.day))}>
      <abbr title={w.name}>{w.short}</abbr>
      <span class="n">{counts[w.day]}<span class="sr-only"> raids</span></span>
    </button>
  {/each}
</div>

<style>
  .chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  button {
    font: inherit;
    font-family: 'Cinzel', Georgia, serif;
    letter-spacing: 0.05em;
    display: inline-flex;
    align-items: baseline;
    gap: 0.4rem;
    min-height: 2.5rem;
    padding: 0.35rem 0.9rem;
    border: 1px solid var(--bronze);
    border-radius: 999px;
    background: rgb(18 15 51 / 0.45);
    color: var(--cream);
    cursor: pointer;
  }
  abbr { text-decoration: none; }
  .n { font-family: 'Alegreya Sans', system-ui, sans-serif; font-size: 0.85rem; color: var(--muted); }
  button[aria-pressed='true'] { background: var(--bronze); color: var(--ink); font-weight: 700; }
  button[aria-pressed='true'] .n { color: var(--ink); }
  button:hover:not([aria-pressed='true']) { background: rgb(63 214 200 / 0.18); }
  button:focus-visible { outline: 2px solid var(--bronze-hi); outline-offset: 2px; }
</style>
