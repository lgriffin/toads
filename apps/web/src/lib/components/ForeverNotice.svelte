<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import '$lib/pond.css';
  import { base } from '$app/paths';
  import { FOREVER_LAUNCH, TAB_PREVIEW, TAB_PURPOSE, tabOf } from '$lib/launch';
  import { memberToads, toadSrc, type MemberFacts } from '$lib/toads';
  import MemberToads from './MemberToads.svelte';
  import ToadGreeting from './ToadGreeting.svelte';
  import ToadsMark from './ToadsMark.svelte';

  // What an officer meets on any member tab while the launch hold is on: their own toad, then the tab's intent and
  // what is coming to it (src/lib/launch.ts). The tab stays in the nav; its page waits for the Forever launch.
  let { path, name, ...facts }: MemberFacts & { path: string; name: string } = $props();
  let tab = $derived(tabOf(path));
  let preview = $derived(tab ? TAB_PREVIEW[tab.href] : undefined);
  let toads = $derived(memberToads(facts));
</script>

<svelte:head><title>{tab?.label ?? 'Coming soon'} · Toads</title></svelte:head>

<div class="pond-page">
  {#if !preview?.ownToads}<ToadGreeting {name} {...facts} />{/if}

  {#if preview && tab}
    <section class="band notice preview" aria-labelledby="notice-h">
      <div class="intro">
        <div>
          <p class="line">Coming with the Forever launch · <time datetime={FOREVER_LAUNCH.date}>{FOREVER_LAUNCH.label}</time></p>
          <h1 id="notice-h">{tab.label} {#if preview.ownToads}<MemberToads {...facts} size={40} />{/if}</h1>
          <p class="intent">{preview.intent}</p>
        </div>
        {#if preview.toad}<img src="{base}/logos/{preview.toad}.svg" alt="" width="132" height="158" />{/if}
      </div>
      {#if preview.ownToads && toads.length}
        <div class="section" role="region" aria-labelledby="own-toads-h">
          <h2 id="own-toads-h">Your toads</h2>
          <ul class="showcase">
            {#each toads as t (t.id)}
              <li><img src={toadSrc(base, t, true)} alt="" width="96" height="115" /><span>{t.label}</span></li>
            {/each}
          </ul>
        </div>
      {/if}
      {#each preview.sections as s (s.title)}
        <div class="section">
          <h2>{s.title}</h2>
          <ul>
            {#each s.items as item (item)}<li>{item}</li>{/each}
          </ul>
        </div>
      {/each}
      {#if preview.showcase}
        <div class="section">
          <h2>Some of the badges you can earn</h2>
          <ul class="showcase">
            {#each preview.showcase as b (b.toad)}
              <li><img src="{base}/logos/{b.toad}.svg" alt="" width="96" height="115" /><span>{b.label}</span></li>
            {/each}
          </ul>
        </div>
      {/if}
    </section>
  {:else}
    <section class="band notice" aria-labelledby="notice-h">
      <ToadsMark size={96} />
      <p class="line">Coming with the Forever launch · <time datetime={FOREVER_LAUNCH.date}>{FOREVER_LAUNCH.label}</time></p>
      <h1 id="notice-h">{tab?.label ?? 'This page'} opens at launch</h1>
      {#if tab && TAB_PURPOSE[tab.href]}<p class="purpose">{TAB_PURPOSE[tab.href]}</p>{/if}
    </section>
  {/if}

  <section class="band dusk close" aria-labelledby="close-h">
    <h2 id="close-h">Why you can see this</h2>
    <p>
      Officers see every tab now so you know where things will live. Raiders see a single coming-soon page until
      launch day.
    </p>
    <div class="actions">
      <a class="ghost" href="{base}/features/">See the hub's features</a>
    </div>
  </section>
</div>

<style>
  .notice {
    justify-items: center;
    text-align: center;
    padding: 3.5rem 0;
    gap: 0.9rem;
    min-height: 22rem;
    align-content: center;
    background: radial-gradient(ellipse 55% 60% at 50% 40%, var(--dusk), var(--ink) 75%);
  }
  .notice :global(svg) { filter: drop-shadow(0 10px 20px rgb(5 3 30 / 0.6)); }
  .notice.preview { justify-items: stretch; text-align: left; align-content: start; gap: 1.8rem; background: var(--ink); }
  .intro { display: grid; grid-template-columns: 1fr auto; gap: 1.5rem; align-items: center; }
  .intro img { filter: drop-shadow(0 10px 20px rgb(5 3 30 / 0.6)); }
  .line { margin: 0; font-family: 'Cinzel', Georgia, serif; letter-spacing: 0.2em; text-transform: uppercase; color: var(--bronze-hi); font-size: 0.85rem; text-wrap: balance; }
  h1 { font-size: clamp(1.9rem, 6vw, 3rem); color: var(--cream); }
  .intro h1 { margin: 0.4rem 0 0.6rem; }
  .intent { margin: 0; max-width: 58ch; font-size: 1.2rem; color: var(--cream); text-wrap: pretty; }
  .purpose { margin: 0; max-width: 52ch; font-size: 1.2rem; text-wrap: balance; }
  .section h2 { font-size: 1.3rem; color: var(--bronze-hi); margin-bottom: 0.6rem; }
  .section ul { margin: 0; padding-left: 1.2rem; display: grid; gap: 0.5rem; max-width: 70ch; }
  .section li::marker { color: var(--teal); }
  .section ul.showcase { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 1.2rem; max-width: none; }
  .showcase li { display: grid; justify-items: center; gap: 0.3rem; color: var(--muted); font-size: 0.95rem; }
  .close { padding: 2.2rem 0; }
  .close p { margin: 0; max-width: 60ch; color: var(--muted); }
  @media (max-width: 36rem) {
    .intro { grid-template-columns: 1fr; }
    .intro img { order: -1; width: 96px; height: auto; }
  }
</style>
