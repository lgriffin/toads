<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { dayName, hubAbsences, raidDaysOf } from '$lib/absences';
  import { previewAbsences, previewRaidSession } from '$lib/preview/absences-fake';
  import { previewSession } from '$lib/preview/session.svelte';
  import DaySwitch from '$lib/components/DaySwitch.svelte';
  import TeamAbsences from '$lib/components/TeamAbsences.svelte';

  // The officers' Calendar: each night they run, the upcoming nights with who is away and every absence ahead, with
  // the member's note. Members add theirs on Me. The API refuses anyone who is not that night's officer.
  let session = $state<Session | null | undefined>(undefined);
  const backend = __PREVIEW__ ? previewAbsences : hubAbsences;
  onMount(async () => {
    if (!__PREVIEW__) session = await getSession().catch(() => null);
  });
  const raidDays = $derived(raidDaysOf(__PREVIEW__ ? previewRaidSession(previewSession.role) : session));
  const ready = $derived(__PREVIEW__ ? previewSession.ready : session !== undefined);
  let picked = $state('');
  const teamDay = $derived(raidDays.officerDays.includes(picked) ? picked : (raidDays.officerDays[0] ?? ''));
</script>

<svelte:head><title>Calendar · Officers · Toads</title></svelte:head>

<div class="calendar">
  <p class="crumb"><a href="{base}/officers/">Officers</a></p>
  <h1>Calendar</h1>
  <p class="lede muted">
    Who has said they will miss a raid night, and why, so you can plan the roster ahead. Members add, change and delete
    their own absences on their <a href="{base}/me/#absences">Me page</a>.
  </p>

  {#if !ready}
    <p class="muted" role="status">Loading…</p>
  {:else if !teamDay}
    <section class="card">
      <p>The Calendar is for a raid night's officers. You do not run a raid night, so there is nothing to show here.</p>
    </section>
  {:else}
    <section class="card officers" aria-labelledby="officers-h">
      <div class="officers-head">
        <h2 id="officers-h">Team absences</h2>
        <DaySwitch days={raidDays.officerDays} names={raidDays.names} bind:value={() => teamDay, (v) => (picked = v)} label="Team" />
      </div>
      <p class="muted">Everyone on {dayName(teamDay, raidDays.names)} who has said they will miss a night.</p>
      <TeamAbsences {backend} day={teamDay} name={dayName(teamDay, raidDays.names)} heading={false} />
    </section>
  {/if}
</div>

<style>
  .calendar { font-family: 'Alegreya Sans', system-ui, sans-serif; font-size: 1.05rem; }
  .calendar :global(h2) { font-family: 'Cinzel', Georgia, serif; font-weight: 600; color: var(--bronze-hi); letter-spacing: 0.03em; }
  h1 { font-family: 'Cinzel', Georgia, serif; color: var(--bronze-hi); letter-spacing: 0.04em; }
  .crumb { margin: 0 0 0.25rem; font-size: 0.95rem; }
  .lede { margin: -0.5rem 0 1.25rem; max-width: 62ch; }
  .officers { display: grid; gap: 0.75rem; }
  .officers h2 { margin: 0; }
  .officers p { margin: 0; }
  .officers-head { display: flex; flex-wrap: wrap; gap: 0.75rem 1.25rem; align-items: center; }
</style>
