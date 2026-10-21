<script lang="ts">
  import { afterNavigate } from '$app/navigation';
  import type { Snippet } from 'svelte';

  // One top bar menu: a button that shows and hides a panel of links (the disclosure pattern, not an application
  // menu, so links stay links and Tab moves through them). Escape closes it and hands focus back to the button; so does
  // a click or focus anywhere outside it, and following one of its links.
  let {
    label,
    prefix,
    current = false,
    align = 'start',
    id,
    open = $bindable(false),
    children
  }: {
    label: string;
    /** Read out before the label by screen readers only, e.g. "Account:" before a member's name. */
    prefix?: string;
    /** The reader is on one of this menu's pages: the button wears the same mark as the current page's link. */
    current?: boolean;
    align?: 'start' | 'end';
    id: string;
    /** Bind it to close the menu from outside, e.g. after a preview view switch. */
    open?: boolean;
    children: Snippet;
  } = $props();

  let root = $state<HTMLElement>();
  let button = $state<HTMLButtonElement>();

  afterNavigate(() => (open = false));

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape' && open) {
      open = false;
      button?.focus();
    }
  }
  // Tabbing out closes it. Focus going nowhere (a pressed button that removed itself) does not; a click outside does.
  function onFocusOut(e: FocusEvent) {
    const to = e.relatedTarget as Node | null;
    if (open && root && to && !root.contains(to)) open = false;
  }
  // Pointer down, not click: a click on a button that removes itself (a preview view switch) would look outside.
  function onWindowPointerDown(e: PointerEvent) {
    if (open && root && !root.contains(e.target as Node)) open = false;
  }
</script>

<svelte:window onpointerdown={onWindowPointerDown} />

<div class="menu" bind:this={root} onkeydown={onKeydown} onfocusout={onFocusOut} role="presentation">
  <button
    bind:this={button}
    type="button"
    class:current
    aria-expanded={open}
    aria-controls={id}
    onclick={() => (open = !open)}
  >
    {#if prefix}<span class="sr-only">{prefix}</span>{/if}<span class="label">{label}</span>
    <svg class="chev" viewBox="0 0 12 12" width="12" height="12" aria-hidden="true"><path d="M2.5 4.5 6 8l3.5-3.5" /></svg>
  </button>
  <div class="panel {align}" {id} hidden={!open}>
    {@render children()}
  </div>
</div>

<style>
  .menu { position: relative; }
  button {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    min-height: 2.75rem;
    padding: 0 0.75rem;
    border: 1px solid transparent;
    border-radius: 8px;
    background: none;
    color: var(--nav-text);
    font: inherit;
    cursor: pointer;
  }
  button:hover, button[aria-expanded='true'] { color: var(--text); background: var(--nav-hover); }
  button.current { color: var(--text); box-shadow: inset 0 -2px 0 var(--accent); border-radius: 8px 8px 2px 2px; }
  .label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 12rem; }
  .chev { fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; transform-origin: center; transition: transform 150ms ease-out; }
  button[aria-expanded='true'] .chev { transform: rotate(180deg); }
  .panel {
    position: absolute;
    top: calc(100% + 0.4rem);
    z-index: 20;
    min-width: 17rem;
    max-width: min(22rem, calc(100vw - 2rem));
    padding: 0.5rem;
    background: var(--menu-bg);
    border: 1px solid var(--line);
    border-radius: 10px;
    box-shadow: 0 12px 28px var(--shadow);
  }
  .panel.start { left: 0; }
  .panel.end { right: 0; }
  .panel[hidden] { display: none; }
  @media (prefers-reduced-motion: reduce) { .chev { transition: none; } }
  /* On a phone the panel spans the screen under the top bar, so nothing is cut off at either edge. */
  @media (max-width: 40rem) {
    .menu { position: static; }
    .panel { left: 0.5rem; right: 0.5rem; top: auto; margin-top: 0.4rem; max-width: none; min-width: 0; }
  }
</style>
