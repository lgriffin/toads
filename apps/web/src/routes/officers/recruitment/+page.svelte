<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { hubPanels } from '$lib/interview-panels';
  import InterviewPanelCard from '$lib/components/InterviewPanelCard.svelte';
  import { previewPanels } from '$lib/preview/panels-fake';
  import { previewSession } from '$lib/preview/session.svelte';

  // Each raid night's officers pick its interview panel; global officers and super admins see every night. The API
  // checks it per night.
  let session = $state<Session | null>(null);
  let loaded = $state(__PREVIEW__);
  onMount(async () => {
    if (__PREVIEW__) return;
    session = await getSession().catch(() => null);
    loaded = true;
  });
  const PREVIEW_NAMES: Record<string, string> = { wed: 'Wednesday', thu: 'Thursday', sun: 'Sunday' };
  const days = $derived(
    __PREVIEW__ ? (previewSession.role === 'admin' ? ['wed', 'thu', 'sun'] : ['wed']) : (session?.officer_days ?? [])
  );
  const names = $derived(__PREVIEW__ ? PREVIEW_NAMES : (session?.day_names ?? {}));
  const backend = __PREVIEW__ ? previewPanels() : hubPanels();
</script>

<svelte:head><title>Recruitment · Toads</title></svelte:head>

<p class="crumbs"><a href="{base}/officers">Officer console</a></p>
<h1>Recruitment</h1>
{#if !loaded}
  <p class="muted" role="status">Loading…</p>
{:else if days.length === 0}
  <p class="muted">Interview panels are set by the officers of each raid night.</p>
{:else}
  <p class="lede">
    Applicants pick their raid night on the recruit page. The Toad Bot opens their interview room with that night's
    panel the moment they apply.
  </p>
  <div class="nights">
    {#each days as day (day)}
      <InterviewPanelCard {backend} {day} night={names[day] ?? day} />
    {/each}
  </div>
{/if}

<style>
  .crumbs { margin: 0 0 0.5rem; font-size: 0.9rem; }
  .lede { max-width: 60ch; }
  .nights { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr)); }
</style>
