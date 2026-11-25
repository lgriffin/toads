<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { dayName, raidDaysOf } from '$lib/absences';
  import { previewRaidSession } from '$lib/preview/absences-fake';
  import { previewSignIns } from '$lib/preview/sign-ins-fake';
  import { previewSession } from '$lib/preview/session.svelte';
  import { dayLabel, hubSignIns, isoDay, shiftDay } from '$lib/sign-ins';
  import SignInAudit from '$lib/components/SignInAudit.svelte';

  // The officers' sign-in audit: one panel for each raid night the viewer runs, holding that night's members only, so a
  // Sunday officer never sees who on Wednesday signs in. Global officers and super admins run every night and also see
  // members on no raid night. The API refuses anyone who is not that night's officer.
  let session = $state<Session | null | undefined>(undefined);
  const backend = __PREVIEW__ ? previewSignIns : hubSignIns();
  onMount(async () => {
    if (!__PREVIEW__) session = await getSession().catch(() => null);
  });
  const raidDays = $derived(raidDaysOf(__PREVIEW__ ? previewRaidSession(previewSession.role) : session));
  const ready = $derived(__PREVIEW__ ? previewSession.ready : session !== undefined);
  const globalTier = $derived(__PREVIEW__ ? previewSession.role === 'admin' : !!session?.global_officer);

  const today = isoDay(new Date());
  let on = $state(today);
  const pick = (date: string) => (on = date > today ? today : date);
</script>

<svelte:head><title>Sign-ins · Officers · toads</title></svelte:head>

<div class="signins-page">
  <p class="crumb"><a href="{base}/officers/">Officers</a></p>
  <h1>Sign-ins</h1>
  <p class="lede muted">
    Who signed in to the hub on a day, and when each member of your raid night last did. Pick a day below, or a bar in
    a night's last fortnight. Members who have not signed in for two weeks are shown in italics.
  </p>

  {#if !ready}
    <p class="muted" role="status">Loading…</p>
  {:else if !raidDays.officerDays.length && !globalTier}
    <section class="card">
      <p>Sign-ins are shown to a raid night's officers. You do not run a raid night, so there is nothing to show here.</p>
    </section>
  {:else}
    <div class="picker" role="group" aria-label="Day">
      <button type="button" class="btn" onclick={() => pick(shiftDay(on, -1))} aria-label="Day before">‹</button>
      <label>
        <span class="sr">Day</span>
        <input type="date" value={on} max={today} onchange={(e) => e.currentTarget.value && pick(e.currentTarget.value)} />
      </label>
      <button type="button" class="btn" onclick={() => pick(shiftDay(on, 1))} disabled={on >= today} aria-label="Day after">›</button>
      {#if on !== today}<button type="button" class="btn link" onclick={() => pick(today)}>Today</button>{/if}
      <span class="muted">{dayLabel(on)}</span>
    </div>
    <div class="nights">
      {#each raidDays.officerDays as day (day)}
        <SignInAudit {backend} {day} title="{dayName(day, raidDays.names)} members" {on} onpick={pick} />
      {/each}
      {#if globalTier}
        <SignInAudit {backend} day={null} title="Members on no raid night" {on} onpick={pick} />
      {/if}
    </div>
  {/if}
</div>

<style>
  .signins-page { font-family: 'Alegreya Sans', system-ui, sans-serif; font-size: 1.05rem; }
  .signins-page :global(h2) { font-family: 'Cinzel', Georgia, serif; font-weight: 600; color: var(--bronze-hi); letter-spacing: 0.03em; }
  h1 { font-family: 'Cinzel', Georgia, serif; color: var(--bronze-hi); letter-spacing: 0.04em; }
  .crumb { margin: 0 0 0.25rem; font-size: 0.95rem; }
  .lede { margin: -0.5rem 0 1.25rem; max-width: 62ch; }
  .picker { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; margin-block-end: 1rem; }
  .sr { position: absolute; inline-size: 1px; block-size: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
  .nights { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr)); }
</style>
