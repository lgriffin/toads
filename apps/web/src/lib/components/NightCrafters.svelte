<script lang="ts">
  import { base } from '$app/paths';
  import { crafterGroups, describe, getNightCrafters, type NightCrafter } from '$lib/professions';
  import { previewNightCrafters } from '$lib/preview/professions-fake';

  // The Raid page's guild crafters (docs/professions.md): the members officers named as the guild's crafters who are
  // on this night, so its raiders know who to send recipes and mats to.
  // `dusk` paints the band dark, so it alternates with the bands around it on the page.
  let { day, name, dusk = false }: { day: string; name: string; dusk?: boolean } = $props();

  let crafters = $state<NightCrafter[] | null>(null);
  let failed = $state(false);
  $effect(() => {
    const night = day;
    crafters = null;
    failed = false;
    const load = __PREVIEW__ ? Promise.resolve(previewNightCrafters(night)) : getNightCrafters(night);
    load.then(
      (c) => {
        if (night === day) crafters = c;
      },
      () => {
        if (night === day) failed = true;
      }
    );
  });
  const groups = $derived(crafters ? crafterGroups(crafters) : []);
</script>

<section class="band" class:dusk aria-labelledby="crafters-h">
  <div class="head">
    <h2 id="crafters-h">Guild crafters</h2>
    <p>
      {name}’s members the officers named as the guild’s crafters. Send them the top end recipes and the mats for what
      you need made. <a href="{base}/setup">Add your own professions in your setup.</a>
    </p>
  </div>
  {#if failed}
    <p class="err" role="alert">Could not load the guild crafters; try again later.</p>
  {:else if crafters === null}
    <p class="muted" role="status">Loading…</p>
  {:else if !groups.length}
    <p class="muted">Nobody on {name} is named a guild crafter yet.</p>
  {:else}
    <ul class="crafts">
      {#each groups as g (g.profession.id)}
        <li>
          <h3>{g.profession.name}</h3>
          <ul>
            {#each g.crafters as c (c.member_id)}
              <li>
                <strong>{c.member_name}</strong>
                {#if describe(c) !== g.profession.name}
                  <span class="muted">{describe(c).slice(g.profession.name.length).trim()}</span>
                {/if}
                {#if c.note}<span class="note">{c.note}</span>{/if}
              </li>
            {/each}
          </ul>
        </li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .crafts { list-style: none; margin: 0; padding: 0; display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); }
  .crafts > li { display: grid; gap: 0.35rem; align-content: start; padding-top: 1rem; border-top: 2px solid var(--bronze); }
  .crafts ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.4rem; }
  .crafts ul li { display: flex; flex-wrap: wrap; gap: 0.15rem 0.5rem; align-items: baseline; }
  .note { flex-basis: 100%; color: var(--muted); }
  h3 { margin: 0; }
</style>
