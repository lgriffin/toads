<script lang="ts">
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { APPS, LOCKED, MORE, TIER_LABEL, standing, tierOf, unlocked, type Tier } from '$lib/access';
  import type { PreviewRole } from '$lib/preview/gate';
  import { previewSession } from '$lib/preview/session.svelte';

  // What each tier can do across the three apps. Public: signed out it shows everything locked, so a visitor can see
  // what joining gets them. The routes behind each row check their own permission; this page only explains.
  let session = $state<Session | null | undefined>(undefined);
  onMount(async () => {
    if (!__PREVIEW__) session = await getSession().catch(() => null);
  });
  const PREVIEW_TIER: Record<PreviewRole, Tier> = { member: 'raider', officer: 'officer', admin: 'admin' };
  let tier = $derived<Tier>(
    __PREVIEW__ ? (previewSession.role ? PREVIEW_TIER[previewSession.role] : 'visitor') : tierOf(session)
  );
</script>

<svelte:head><title>Your toolkit · Toads</title></svelte:head>

<h1>Your toolkit</h1>
<p class="standing">
  <span class="pill">{TIER_LABEL[tier]}</span>
  {standing(tier)}
</p>

<div class="apps">
  {#each APPS as app (app.id)}
    <section class="card app" aria-labelledby="{app.id}-h">
      <header>
        <h2 id="{app.id}-h">{app.title}</h2>
        <p class="muted">{app.where}</p>
      </header>
      {#each app.rows as row (row.tier)}
        {@const open = unlocked(row, tier)}
        <div class="row" class:locked={!open} data-tier={row.tier}>
          <h3>{row.tier === 'visitor' ? 'Everyone' : TIER_LABEL[row.tier]}</h3>
          {#if open}
            <ul>
              {#each row.can as c (c.text)}<li>{c.text}</li>{/each}
            </ul>
          {:else}
            <p class="muted">{LOCKED[row.tier]}</p>
            <ul class="dim" aria-label="{TIER_LABEL[row.tier]} only">
              {#each row.can as c (c.text)}<li>{c.text}</li>{/each}
            </ul>
          {/if}
        </div>
      {/each}
    </section>
  {/each}
</div>

<section class="more" aria-labelledby="more-h">
  <h2 id="more-h">How to get more</h2>
  <ul>
    {#each MORE as m (m.title)}<li class="card"><h3>{m.title}</h3><p>{m.body}</p></li>{/each}
  </ul>
</section>

<style>
  .standing { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; margin: 0 0 1.25rem; max-width: 46rem; }
  .apps { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr)); align-items: start; }
  .app { padding: 0; overflow: hidden; }
  .app header { padding: 1rem; border-bottom: 1px solid var(--line); }
  .app header h2 { margin: 0 0 0.2rem; }
  .app header p { margin: 0; font-size: 0.9rem; }
  .row { padding: 0.75rem 1rem; border-top: 1px solid var(--line); display: grid; gap: 0.3rem; }
  .row:first-of-type { border-top: 0; }
  .row h3 { margin: 0; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--accent); }
  .row ul { margin: 0; padding-left: 1.1rem; display: grid; gap: 0.2rem; font-size: 0.92rem; }
  .row p { margin: 0; font-size: 0.85rem; font-style: italic; }
  .locked h3 { color: var(--muted); }
  .dim { color: var(--muted); }
  .more { margin-top: 2rem; display: grid; gap: 0.75rem; }
  .more h2 { margin: 0; }
  .more ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); }
  .more h3 { margin: 0 0 0.3rem; font-size: 1rem; }
  .more p { margin: 0; }
</style>
