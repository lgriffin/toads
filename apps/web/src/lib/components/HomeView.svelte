<script lang="ts">
  import type { Snippet } from 'svelte';
  import { isWide, shownIds, type HomeLayout, type HomeWidget, type WidgetId } from '$lib/home';
  import HomeCustomiser from './HomeCustomiser.svelte';

  // The signed-in home: the member's widgets in their order, and the customiser. Each page supplies how a widget
  // renders (`widget`), so the preview and the API-backed hub share this layout. `top` is for things that are not
  // widgets and always come first, like a spotlight waiting on the member's consent.
  let {
    name,
    layout,
    save,
    reset,
    widget,
    top
  }: {
    name: string;
    layout: HomeLayout;
    save: (widgets: HomeWidget[]) => Promise<string | null>;
    reset: () => Promise<string | null>;
    widget: Snippet<[WidgetId]>;
    top?: Snippet;
  } = $props();

  let editing = $state(false);
  const shown = $derived(shownIds(layout));

  async function close(action: () => Promise<string | null>): Promise<string | null> {
    const error = await action();
    if (!error) editing = false;
    return error;
  }
</script>

<div class="head">
  <h1>Your night, {name}</h1>
  <button
    class="btn"
    type="button"
    aria-expanded={editing}
    aria-controls={editing ? 'customise' : undefined}
    onclick={() => (editing = !editing)}>{editing ? 'Close customise' : 'Customise'}</button
  >
</div>

{#if editing}
  <HomeCustomiser
    id="customise"
    {layout}
    save={(w) => close(() => save(w))}
    reset={() => close(reset)}
    cancel={() => (editing = false)}
  />
{/if}

{@render top?.()}

<div class="grid home">
  {#each shown as id (id)}
    <div class="slot" class:wide={isWide(id)} data-widget={id}>{@render widget(id)}</div>
  {:else}
    <p class="muted">Your home is empty. Choose Customise to add widgets.</p>
  {/each}
</div>

<style>
  .head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.5rem 1rem; }
  .slot { display: grid; min-width: 0; }
  .slot.wide { grid-column: 1 / -1; }
</style>
