<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { hubComps } from '$lib/comp';
  import { NIGHT_IDS } from '$lib/nights';
  import CompBuilder from '$lib/components/CompBuilder.svelte';
  import { previewComps } from '$lib/preview/comp-fake';
  import { previewSession } from '$lib/preview/session.svelte';

  // Officers build comps for the raid nights they run; global officers for every night. The API checks it per night.
  let session = $state<Session | null>(null);
  let loaded = $state(__PREVIEW__);
  onMount(async () => {
    if (__PREVIEW__) return;
    session = await getSession().catch(() => null);
    loaded = true;
  });
  const days = $derived(
    __PREVIEW__ ? (previewSession.role === 'admin' ? [...NIGHT_IDS] : ['wed']) : (session?.officer_days ?? [])
  );
  const backend = __PREVIEW__ ? previewComps : hubComps();
</script>

<svelte:head><title>Comp builder · Toads</title></svelte:head>

<p class="crumbs"><a href="{base}/officers">Officer console</a></p>
{#if !loaded}
  <p class="muted" role="status">Loading…</p>
{:else if days.length === 0}
  <h1>Raid comp builder</h1>
  <p class="muted">The comp builder is for the officers of each raid night.</p>
{:else}
  <CompBuilder {backend} {days} />
{/if}

<style>
  .crumbs { margin: 0 0 0.5rem; font-size: 0.9rem; }
</style>
