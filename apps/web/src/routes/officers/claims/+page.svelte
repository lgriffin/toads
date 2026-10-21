<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { dayName, raidDaysOf } from '$lib/absences';
  import { hubClaims } from '$lib/officer-claims';
  import { previewRaidSession } from '$lib/preview/absences-fake';
  import { previewClaims } from '$lib/preview/claims-fake';
  import { previewSession } from '$lib/preview/session.svelte';
  import ClaimsQueue from '$lib/components/ClaimsQueue.svelte';

  // The officers' character claims: one panel for each raid night the viewer runs, holding the claims of members whose
  // night Toad role puts them on it. Global officers and super admins run every night, and also see the claims of
  // members on no night. The API refuses anyone who is not that night's officer.
  let session = $state<Session | null | undefined>(undefined);
  const backend = __PREVIEW__ ? previewClaims : hubClaims();
  onMount(async () => {
    if (!__PREVIEW__) session = await getSession().catch(() => null);
  });
  const raidDays = $derived(raidDaysOf(__PREVIEW__ ? previewRaidSession(previewSession.role) : session));
  const ready = $derived(__PREVIEW__ ? previewSession.ready : session !== undefined);
  // A claim on two nights shows on both panels; deciding it on one takes it off the other.
  let decided = $state<number[]>([]);
  const ondecided = (id: number) => (decided = [...decided, id]);
  const globalTier = $derived(__PREVIEW__ ? previewSession.role === 'admin' : !!session?.global_officer);
</script>

<svelte:head><title>Character claims · Officers · Toads</title></svelte:head>

<div class="claims-page">
  <p class="crumb"><a href="{base}/officers/">Officers</a></p>
  <h1>Character claims</h1>
  <p class="lede muted">
    Members claim their characters on Me. A name that matches their Discord nickname is approved straight away; the rest
    wait here for an officer of the member's raid night, which comes from their night Toad role in Discord.
  </p>

  {#if !ready}
    <p class="muted" role="status">Loading…</p>
  {:else if !raidDays.officerDays.length && !globalTier}
    <section class="card">
      <p>Claims are decided by a raid night's officers. You do not run a raid night, so there is nothing to show here.</p>
    </section>
  {:else}
    <div class="nights">
      {#each raidDays.officerDays as day (day)}
        <ClaimsQueue {backend} {day} title="{dayName(day, raidDays.names)} claims" names={raidDays.names} {decided} {ondecided} />
      {/each}
      {#if globalTier}
        <ClaimsQueue {backend} day={null} title="Members on no raid night" names={raidDays.names} {decided} {ondecided} />
      {/if}
    </div>
  {/if}
</div>

<style>
  .claims-page { font-family: 'Alegreya Sans', system-ui, sans-serif; font-size: 1.05rem; }
  .claims-page :global(h2) { font-family: 'Cinzel', Georgia, serif; font-weight: 600; color: var(--bronze-hi); letter-spacing: 0.03em; }
  h1 { font-family: 'Cinzel', Georgia, serif; color: var(--bronze-hi); letter-spacing: 0.04em; }
  .crumb { margin: 0 0 0.25rem; font-size: 0.95rem; }
  .lede { margin: -0.5rem 0 1.25rem; max-width: 62ch; }
  .nights { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr)); }
</style>
