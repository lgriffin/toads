<script lang="ts">
  import type { Snippet } from 'svelte';
  import { base } from '$app/paths';
  import PondScene from './PondScene.svelte';

  // The opening band of a public page: the twilight pond behind a Cinzel title, a line about the page, its actions and
  // the page's own toads standing on the right. Shorter than the homepage hero; the page's content follows at once.
  let {
    title,
    line = '',
    lede,
    toads = [],
    children
  }: {
    title: string;
    /** The small bronze line under the title, such as "Horde · PvP · EU". */
    line?: string;
    lede: string;
    /** Badge files under static/logos/, without `.svg`, standing in a row. */
    toads?: string[];
    children?: Snippet;
  } = $props();
</script>

<section class="pond-hero band" aria-labelledby="page-h">
  <div class="backdrop" aria-hidden="true">
    <PondScene />
    <div class="veil"></div>
  </div>
  <div class="text">
    <h1 id="page-h">{title}</h1>
    {#if line}<p class="line">{line}</p>{/if}
    <p class="lede">{lede}</p>
    {#if children}<div class="actions">{@render children()}</div>{/if}
  </div>
  {#if toads.length}
    <div class="toads" aria-hidden="true">
      {#each toads as t, i (t)}
        <img src="{base}/logos/{t}.svg" alt="" width="150" height="180" style="--i: {i}" />
      {/each}
    </div>
  {/if}
</section>

<style>
  .pond-hero {
    overflow-x: clip;
    min-height: 22rem;
    padding: 3.5rem 0 3rem;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 2rem;
  }
  .backdrop {
    position: absolute;
    inset: 0;
    overflow: hidden;
    mask-image: linear-gradient(to right, transparent, #000 12%, #000 88%, transparent);
  }
  .backdrop :global(svg) { position: absolute; inset: 0; }
  .veil {
    position: absolute;
    inset: 0;
    background:
      linear-gradient(to right, rgb(18 15 51 / 0.88), rgb(18 15 51 / 0.55) 55%, rgb(18 15 51 / 0.2)),
      linear-gradient(to bottom, rgb(18 15 51 / 0.2), rgb(18 15 51 / 0.75));
  }
  .text, .toads { position: relative; }
  .text { display: grid; gap: 0.7rem; justify-items: start; }
  h1 { font-size: clamp(2.2rem, 7vw, 3.8rem); color: var(--cream); letter-spacing: 0.06em; text-shadow: 0 2px 16px rgb(5 3 30 / 0.7); }
  .line { margin: 0; font-family: 'Cinzel', Georgia, serif; letter-spacing: 0.2em; text-transform: uppercase; color: var(--bronze-hi); font-size: 0.9rem; }
  .lede { margin: 0; max-width: 56ch; font-size: 1.2rem; text-shadow: 0 1px 10px rgb(5 3 30 / 0.8); }
  .actions { margin-top: 0.5rem; }
  .toads { display: flex; align-items: flex-end; }
  .toads img {
    width: clamp(6.5rem, 12vw, 9.5rem);
    height: auto;
    margin-left: -1.6rem;
    filter: drop-shadow(0 10px 18px rgb(5 3 30 / 0.6));
    transform: translateY(calc(var(--i) * -0.6rem)) rotate(calc((var(--i) - 1) * 4deg));
  }
  .toads img:first-child { margin-left: 0; }
  @media (max-width: 52rem) {
    .pond-hero { grid-template-columns: 1fr; }
    /* On a phone the title leads; the toads would only crowd it. */
    .toads { display: none; }
  }
</style>
