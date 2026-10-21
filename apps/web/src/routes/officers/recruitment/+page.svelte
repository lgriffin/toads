<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { hubPanels } from '$lib/interview-panels';
  import DecisionsCard from '$lib/components/DecisionsCard.svelte';
  import InterviewPanelCard from '$lib/components/InterviewPanelCard.svelte';
  import { hubDecisions } from '$lib/decisions';
  import { NIGHT_IDS, NIGHT_NAMES } from '$lib/nights';
  import { previewDecisions } from '$lib/preview/decisions-fake';
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
  const days = $derived(
    __PREVIEW__ ? (previewSession.role === 'admin' ? [...NIGHT_IDS] : ['wed']) : (session?.officer_days ?? [])
  );
  const names = $derived(__PREVIEW__ ? NIGHT_NAMES : (session?.day_names ?? {}));
  const backend = __PREVIEW__ ? previewPanels() : hubPanels();
  const decisions = __PREVIEW__ ? previewDecisions() : hubDecisions();
</script>

<svelte:head><title>Recruitment · Toads</title></svelte:head>

<p class="crumbs"><a href="{base}/officers">Officer console</a></p>
<h1>Recruitment</h1>
{#if !loaded}
  <p class="muted" role="status">Loading…</p>
{:else if days.length === 0}
  <p class="muted">Decisions and interview panels belong to the officers of each raid night.</p>
{:else}
  <p class="lede">
    Applicants pick their raid night on the recruit page. The Toad Bot opens their interview room with that night's
    panel the moment they apply.
  </p>

  <h2 class="section">Decisions</h2>
  <p class="lede">
    Any officer of the night can leave a note while an applicant waits. Rejecting declines the application and deletes
    the interview room; accepting gives them the night's raider role in Discord.
  </p>
  <div class="nights">
    {#each days as day (day)}
      <DecisionsCard backend={decisions} {day} night={names[day] ?? day} />
    {/each}
  </div>

  <h2 class="section">Interview panels</h2>
  <div class="nights">
    {#each days as day (day)}
      <InterviewPanelCard {backend} {day} night={names[day] ?? day} />
    {/each}
  </div>
{/if}

<style>
  .crumbs { margin: 0 0 0.5rem; font-size: 0.9rem; }
  .lede { max-width: 60ch; }
  .section { margin: 1.75rem 0 0.25rem; }
  .nights { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr)); }
</style>
