<script lang="ts">
  import type { Raid } from '$lib/strategy';

  // Picks the raids a night is running (docs/strategy.md): a dropdown of ticks, so a night that runs two raids picks
  // both. The night runs them in the order they were ticked; unticking one keeps the others' order.
  let {
    label,
    raids,
    chosen,
    disabled = false,
    onchange
  }: { label: string; raids: Raid[]; chosen: string[]; disabled?: boolean; onchange: (raids: string[]) => void } =
    $props();

  let box = $state<HTMLDetailsElement | null>(null);
  const shorts = $derived(chosen.map((id) => raids.find((r) => r.id === id)?.short ?? id));
  const summary = $derived(shorts.length ? shorts.join(' then ') : 'Not decided yet');

  function toggle(id: string, on: boolean) {
    onchange(on ? [...chosen.filter((r) => r !== id), id] : chosen.filter((r) => r !== id));
  }
  function away(e: MouseEvent) {
    if (box?.open && !box.contains(e.target as Node)) box.open = false;
  }
  function escape(e: KeyboardEvent) {
    if (e.key === 'Escape' && box?.open) {
      box.open = false;
      box.querySelector('summary')?.focus();
    }
  }
</script>

<svelte:window onclick={away} onkeydown={escape} />

<details class="picker" bind:this={box}>
  <summary aria-label="{label}: {summary}" class:disabled>{summary}</summary>
  <fieldset {disabled}>
    <legend>{label}</legend>
    {#each raids as r (r.id)}
      <label>
        <input
          type="checkbox"
          checked={chosen.includes(r.id)}
          onchange={(e) => toggle(r.id, (e.currentTarget as HTMLInputElement).checked)}
        />
        <span><strong>{r.short}</strong> {r.name}</span>
        {#if chosen.includes(r.id) && chosen.length > 1}
          <span class="nth muted">{chosen.indexOf(r.id) + 1}</span>
        {/if}
      </label>
    {/each}
    <p class="muted">Tick one or more, in the order the night runs them.</p>
  </fieldset>
</details>

<style>
  .picker { display: inline-block; max-width: 100%; vertical-align: top; }
  summary {
    cursor: pointer; list-style: none; padding: 0.35rem 2rem 0.35rem 0.6rem; border-radius: 6px; min-width: 12rem;
    border: 1px solid var(--line); background: var(--surface); position: relative;
  }
  summary::-webkit-details-marker { display: none; }
  summary::after { content: '▾'; position: absolute; right: 0.6rem; top: 50%; transform: translateY(-50%); }
  .picker[open] summary::after { content: '▴'; }
  summary.disabled { opacity: 0.6; }
  /* It opens in the flow, below its summary, so the band after it never covers it. */
  fieldset {
    margin: 0.25rem 0 0; min-width: min(100%, 17rem); box-sizing: border-box;
    display: grid; gap: 0.15rem; padding: 0.5rem; border-radius: 8px; border: 1px solid var(--line);
    background: var(--menu-bg); box-shadow: 0 12px 28px var(--shadow);
  }
  legend { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
  label { display: flex; gap: 0.5rem; align-items: center; padding: 0.3rem 0.35rem; border-radius: 6px; cursor: pointer; }
  label:hover { background: var(--nav-hover); }
  .nth { margin-left: auto; font-size: 0.85rem; }
  fieldset p { margin: 0.25rem 0.35rem 0; font-size: 0.85rem; }
</style>
