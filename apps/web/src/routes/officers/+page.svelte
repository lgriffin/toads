<script lang="ts">
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

{#if __PREVIEW__}
  <Officers />
  {#if globalTier}
    <AwardsDesk backend={previewAwards} />
  {:else}
    <p class="muted">Awards are given by global officers. Switch to the super admin view to try the awards desk.</p>
  {/if}
{:else}
  <h1>Officer console</h1>
  <p>Applications, the Discord curation queue, post composer, highlight review and spotlights arrive with the API.</p>
  <ReferenceCard />
  {#if globalTier}<AwardsDesk backend={hub} />{/if}
{/if}
