<script lang="ts">
  // Picks the strategy docs a night pins for its raiders (docs/strategy.md): a dropdown of ticks, raid by raid, so a
  // night running two raids pins a doc for each. The Raid page lists them in the order they were ticked; unticking one
  // keeps the others' order.
  type Option = { id: string; short: string; name: string };
  let {
    label,
    options,
    chosen,
    disabled = false,
    empty = 'No docs pinned',
    onchange
  }: {
    label: string;
    options: Option[];
    chosen: string[];
    disabled?: boolean;
    empty?: string;
    /** Saves the new list; false when the save failed, so the tick goes back. */
    onchange: (chosen: string[]) => Promise<boolean>;
  } = $props();

  let box = $state<HTMLDetailsElement | null>(null);
  const summary = $derived(
    chosen
      .flatMap((id) => options.filter((o) => o.id === id))
      .map((o) => `${o.short}: ${o.name}`)
      .join(', ') || empty
  );

  async function toggle(box: HTMLInputElement, id: string) {
    const on = box.checked;
    const saved = await onchange(on ? [...chosen.filter((r) => r !== id), id] : chosen.filter((r) => r !== id));
    // A failed save leaves `chosen` as it was, so put this tick back to match it.
    if (!saved) box.checked = chosen.includes(id);
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
    {#each options as o (o.id)}
      <label>
        <input
          type="checkbox"
          checked={chosen.includes(o.id)}
          onchange={(e) => toggle(e.currentTarget as HTMLInputElement, o.id)}
        />
        <span><strong>{o.short}</strong> {o.name}</span>
        {#if chosen.includes(o.id) && chosen.length > 1}
          <span class="nth muted">{chosen.indexOf(o.id) + 1}</span>
        {/if}
      </label>
    {:else}
      <p class="muted">No docs added yet.</p>
    {/each}
    {#if options.length}<p class="muted">Tick one or more, in the order raiders should open them.</p>{/if}
  </fieldset>
</details>

<style>
  .picker { display: inline-block; max-width: 100%; vertical-align: top; }
  summary {
    cursor: pointer; list-style: none; padding: 0.35rem 2rem 0.35rem 0.6rem; border-radius: 6px; min-width: 12rem;
    overflow-wrap: anywhere;
    border: 1px solid var(--line); background: var(--surface); position: relative;
  }
  summary::-webkit-details-marker { display: none; }
  summary::after { content: '▾'; position: absolute; right: 0.6rem; top: 50%; transform: translateY(-50%); }
  .picker[open] summary::after { content: '▴'; }
  summary.disabled { opacity: 0.6; }
  /* It opens in the flow, below its summary, so the band after it never covers it. */
  fieldset {
    margin: 0.25rem 0 0; min-width: min(100%, 20rem); box-sizing: border-box;
    display: grid; gap: 0.15rem; padding: 0.5rem; border-radius: 8px; border: 1px solid var(--line);
    background: var(--menu-bg); box-shadow: 0 12px 28px var(--shadow);
  }
  legend { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
  label { display: flex; gap: 0.5rem; align-items: center; padding: 0.3rem 0.35rem; border-radius: 6px; cursor: pointer; }
  label:hover { background: var(--nav-hover); }
  .nth { margin-left: auto; font-size: 0.85rem; }
  fieldset p { margin: 0.25rem 0.35rem 0; font-size: 0.85rem; }
</style>
