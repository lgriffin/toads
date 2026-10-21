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
  const lead = $derived(shown[0] === 'my_performance' ? shown[0] : null);
  const rest = $derived(lead ? shown.slice(1) : shown);

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

<!-- The member's own last raid leads when it is first; anything waiting on them (a spotlight to consent to) follows. -->
{#if lead}
  <div class="grid home lead">
    <div class="slot wide" data-widget={lead}>{@render widget(lead)}</div>
  </div>
{/if}

{@render top?.()}

<div class="grid home">
  {#each rest as id (id)}
    <div class="slot" class:wide={isWide(id)} data-widget={id}>{@render widget(id)}</div>
  {:else}
    {#if !lead}<p class="muted">Your home is empty. Choose Customise to add widgets.</p>{/if}
  {/each}
</div>

<style>
  .head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.5rem 1rem; }
  /* minmax(0, 1fr) and min-width: 0 let wide tables scroll inside their card instead of widening the page. */
  .slot { display: grid; grid-template-columns: minmax(0, 1fr); min-width: 0; }
  .slot > :global(*) { min-width: 0; }
  .slot.wide { grid-column: 1 / -1; }
  .lead { margin-bottom: 1rem; }
</style>
