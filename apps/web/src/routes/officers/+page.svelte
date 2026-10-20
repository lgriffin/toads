<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, listMembers, type Session } from '$lib/api';
  import { giveAward, guildAwards, takeBackAward, type AwardsBackend } from '$lib/awards';
  import AwardsDesk from '$lib/components/AwardsDesk.svelte';
  import ReferenceCard from '$lib/components/ReferenceCard.svelte';
  import Officers from '$lib/preview/Officers.svelte';
  import { previewAwards } from '$lib/preview/awards-fake';
  import { previewSession } from '$lib/preview/session.svelte';

  // Awards are guild-wide, so only global officers (and super admins) give them; the API enforces it.
  let session = $state<Session | null>(null);
  onMount(async () => {
    if (!__PREVIEW__) session = await getSession().catch(() => null);
  });
  const hub: AwardsBackend = {
    wall: () => guildAwards(),
    members: () => listMembers(),
    give: (b) => giveAward(b),
    takeBack: (id) => takeBackAward(id)
  };
  const globalTier = $derived(__PREVIEW__ ? previewSession.role === 'admin' : !!session?.global_officer);
</script>

<svelte:head><title>Officers · Toads</title></svelte:head>

{#snippet compLink()}
  <section class="card comp-link" aria-labelledby="comp-link-h">
    <h2 id="comp-link-h">Raid comp builder</h2>
    <p class="muted">
      Drag specs into groups to see a comp's buffs, or switch to your night's roster and seat members by the primary and
      secondary specs they set on Me.
    </p>
    <a class="btn primary" href="{base}/officers/comp">Open the comp builder</a>
  </section>
  <section class="card comp-link" aria-labelledby="recruit-link-h">
    <h2 id="recruit-link-h">Recruitment</h2>
    <p class="muted">
      Pick who from the Toads Discord interviews each night's applicants. Someone applying for Sunday meets the Sunday
      panel in their interview room.
    </p>
    <a class="btn primary" href="{base}/officers/recruitment">Set interview panels</a>
  </section>
{/snippet}

{#if __PREVIEW__}
  <Officers />
  {@render compLink()}
  {#if globalTier}
    <AwardsDesk backend={previewAwards} />
  {:else}
    <p class="muted">Awards are given by global officers. Switch to the super admin view to try the awards desk.</p>
  {/if}
{:else}
  <h1>Officer console</h1>
  <p>Applications, the Discord curation queue, post composer, highlight review and spotlights arrive with the API.</p>
  {@render compLink()}
  <ReferenceCard />
  {#if globalTier}<AwardsDesk backend={hub} />{/if}
{/if}

<style>
  .comp-link { display: grid; gap: 0.6rem; justify-items: start; margin-block: 1rem; }
  .comp-link h2, .comp-link p { margin: 0; }
</style>
