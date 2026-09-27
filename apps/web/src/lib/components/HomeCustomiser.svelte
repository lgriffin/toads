<script lang="ts">
  import { untrack } from 'svelte';
  import { move, toggle, type HomeLayout, type HomeWidget } from '$lib/home';

  // `save` and `reset` resolve to an error message, or null when they worked.
  let {
    id,
    layout,
    save,
    reset,
    cancel
  }: {
    id: string;
    layout: HomeLayout;
    save: (widgets: HomeWidget[]) => Promise<string | null>;
    reset: () => Promise<string | null>;
    cancel: () => void;
  } = $props();

  // A working copy: nothing changes on the home until Save.
  let draft = $state<HomeWidget[]>(untrack(() => layout.widgets.map((w) => ({ ...w }))));
  let busy = $state(false);
  let error = $state('');

  async function run(action: () => Promise<string | null>) {
    busy = true;
    error = '';
    error = (await action()) ?? '';
    busy = false;
  }
</script>

<section class="card customiser" {id} aria-labelledby="{id}-h">
  <h2 id="{id}-h">Customise your home</h2>
  <p class="muted">Tick the widgets you want and use the arrows to put them in order.</p>
  <ol class="widgets">
    {#each draft as w, i (w.id)}
      <li>
        <label>
          <input type="checkbox" checked={w.shown} disabled={busy} onchange={() => (draft = toggle(draft, w.id))} />
          <span>
            <strong>{w.title}</strong>
            {#if w.officer_only}<span class="pill">Officers</span>{/if}
            <span class="muted small">{w.description}</span>
          </span>
        </label>
        <span class="order">
          <button
            class="btn"
            type="button"
            aria-label="Move {w.title} up"
            disabled={busy || i === 0}
            onclick={() => (draft = move(draft, w.id, -1))}>↑</button
          >
          <button
            class="btn"
            type="button"
            aria-label="Move {w.title} down"
            disabled={busy || i === draft.length - 1}
            onclick={() => (draft = move(draft, w.id, 1))}>↓</button
          >
        </span>
      </li>
    {/each}
  </ol>
  {#if error}<p class="err" role="alert">{error}</p>{/if}
  <div class="actions">
    <button class="btn primary" type="button" disabled={busy} onclick={() => run(() => save(draft))}>Save</button>
    <button class="btn" type="button" disabled={busy} onclick={cancel}>Cancel</button>
    <button class="btn" type="button" disabled={busy || !layout.customised} onclick={() => run(reset)}
      >Reset to default</button
    >
  </div>
</section>

<style>
  .customiser { margin-bottom: 1rem; border-color: var(--accent); }
  .widgets { list-style: none; margin: 0 0 1rem; padding: 0; display: grid; gap: 0.25rem; }
  .widgets li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--line);
  }
  label { display: flex; gap: 0.6rem; align-items: flex-start; min-width: 0; cursor: pointer; }
  label input { margin-top: 0.2rem; }
  label > span { display: flex; flex-wrap: wrap; gap: 0.1rem 0.5rem; min-width: 0; }
  .small { font-size: 0.8rem; flex-basis: 100%; }
  .order { display: flex; gap: 0.35rem; flex-shrink: 0; }
  .order .btn { padding: 0.3rem 0.6rem; }
  .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
</style>
