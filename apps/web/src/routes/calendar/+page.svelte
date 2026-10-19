<script lang="ts">
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { dayName, hubAbsences, raidDaysOf } from '$lib/absences';
  import { previewAbsences, previewRaidSession } from '$lib/preview/absences-fake';
  import { previewSession } from '$lib/preview/session.svelte';
  import AbsenceCalendar from '$lib/components/AbsenceCalendar.svelte';
  import DaySwitch from '$lib/components/DaySwitch.svelte';
  import TeamAbsences from '$lib/components/TeamAbsences.svelte';

  // Members report the raid nights they will miss; officers see their nights' absences below. The API checks both.
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

<svelte:head><title>Calendar · Toads</title></svelte:head>

<h1>Calendar</h1>
<p class="lede muted">Your raid nights, and the ones you cannot make. Tell the officers here instead of in a Discord thread.</p>

{#if !ready}
  <p class="muted" role="status">Loading…</p>
{:else}
  <AbsenceCalendar {backend} {raidDays} />

  {#if teamDay}
    <section class="card officers" aria-labelledby="officers-h">
      <div class="officers-head">
        <h2 id="officers-h">Team absences</h2>
        <DaySwitch days={raidDays.officerDays} names={raidDays.names} bind:value={() => teamDay, (v) => (picked = v)} label="Team" />
      </div>
      <p class="muted">Everyone on {dayName(teamDay, raidDays.names)} who has said they will miss a night, for its officers.</p>
      <TeamAbsences {backend} day={teamDay} name={dayName(teamDay, raidDays.names)} />
    </section>
  {/if}
{/if}

<style>
  h1 { font-family: 'Cinzel', Georgia, serif; color: var(--bronze-hi); letter-spacing: 0.04em; }
  .lede { margin: -0.5rem 0 1.25rem; max-width: 62ch; }
  .officers { margin-top: 1rem; display: grid; gap: 0.75rem; }
  .officers h2 { margin: 0; }
  .officers p { margin: 0; }
  .officers-head { display: flex; flex-wrap: wrap; gap: 0.75rem 1.25rem; align-items: center; }
</style>
