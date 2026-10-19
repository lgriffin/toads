<script lang="ts">
  import { dayName } from '$lib/absences';

  // Switches between raid nights when the viewer sees more than one (super admins, global officers, members on both
  // teams). One button per night; the pressed one is showing.
  let {
    days,
    names,
    value = $bindable(),
    label = 'Raid night'
  }: { days: string[]; names: Record<string, string>; value: string; label?: string } = $props();
</script>

{#if days.length > 1}
  <div class="switch" role="group" aria-label={label}>
    {#each days as d (d)}
      <button type="button" aria-pressed={value === d} onclick={() => (value = d)}>{dayName(d, names)}</button>
    {/each}
  </div>
{/if}

<style>
  .switch {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0;
    border: 1px solid var(--bronze);
    border-radius: 999px;
    overflow: hidden;
    justify-self: start;
  }
  button {
    font: inherit;
    font-family: 'Cinzel', Georgia, serif;
    letter-spacing: 0.06em;
    padding: 0.45rem 1.1rem;
    background: rgb(18 15 51 / 0.45);
    color: var(--cream);
    border: 0;
    cursor: pointer;
  }
  button + button { border-left: 1px solid var(--bronze); }
  button[aria-pressed='true'] { background: var(--bronze); color: var(--ink); font-weight: 700; }
  button:hover:not([aria-pressed='true']) { background: rgb(63 214 200 / 0.18); }
  button:focus-visible { outline: 2px solid var(--bronze-hi); outline-offset: -3px; }
</style>
