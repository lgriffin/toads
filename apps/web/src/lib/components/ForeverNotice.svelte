<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import '$lib/pond.css';
  import { base } from '$app/paths';
  import { FOREVER_LAUNCH, TAB_PURPOSE, tabOf } from '$lib/launch';
  import ToadsMark from './ToadsMark.svelte';

  // What an officer meets on any member tab while the launch hold is on: the tab stays in the nav, its page waits for
  // the Forever launch, and this says what it will hold.
  let { path }: { path: string } = $props();
  let tab = $derived(tabOf(path));
</script>

<svelte:head><title>{tab?.label ?? 'Coming soon'} · Toads</title></svelte:head>

<div class="pond-page">
  <section class="band notice" aria-labelledby="notice-h">
    <ToadsMark size={96} />
    <p class="line">Coming with the Forever launch · <time datetime={FOREVER_LAUNCH.date}>{FOREVER_LAUNCH.label}</time></p>
    <h1 id="notice-h">{tab?.label ?? 'This page'} opens at launch</h1>
    {#if tab && TAB_PURPOSE[tab.href]}<p class="purpose">{TAB_PURPOSE[tab.href]}</p>{/if}
    <p class="muted">
      Officers can see every tab now so you know where things will live. Raiders see a single coming-soon page until
      launch day.
    </p>
    <div class="actions">
      <a class="ghost" href="{base}/toolkit/">See what officers can do</a>
    </div>
  </section>
</div>

<style>
  .notice {
    justify-items: center;
    text-align: center;
    padding: 4rem 0;
    gap: 0.9rem;
    min-height: 26rem;
    align-content: center;
    background: radial-gradient(ellipse 55% 60% at 50% 40%, var(--dusk), var(--ink) 75%);
  }
  .notice :global(svg) { filter: drop-shadow(0 10px 20px rgb(5 3 30 / 0.6)); }
  .line { margin: 0; font-family: 'Cinzel', Georgia, serif; letter-spacing: 0.2em; text-transform: uppercase; color: var(--bronze-hi); font-size: 0.85rem; text-wrap: balance; }
  h1 { font-size: clamp(1.9rem, 6vw, 3rem); color: var(--cream); }
  .purpose { margin: 0; max-width: 52ch; font-size: 1.2rem; text-wrap: balance; }
  .muted { margin: 0; max-width: 56ch; }
  .actions { justify-content: center; margin-top: 0.4rem; }
</style>
