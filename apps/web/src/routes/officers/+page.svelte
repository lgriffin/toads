<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, listMembers, type Session } from '$lib/api';
  import { giveAward, guildAwards, takeBackAward, type AwardsBackend } from '$lib/awards';
  import AwardsDesk from '$lib/components/AwardsDesk.svelte';
  import ReferenceCard from '$lib/components/ReferenceCard.svelte';
  import OfficerNights from '$lib/components/OfficerNights.svelte';
  import { raidDaysOf } from '$lib/absences';
  import { previewRaidSession } from '$lib/preview/absences-fake';
  import { previewAwards } from '$lib/preview/awards-fake';
  import { previewSession } from '$lib/preview/session.svelte';

  // Awards are guild-wide, so only global officers (and super admins) give them; the API enforces it.
  let session = $state<Session | null>(null);
  onMount(async () => {
    if (!__PREVIEW__) session = await getSession().catch(() => null);
  });
  // The preview is this same console, answered from sample data in the browser, so it shows what officers really get.
  const hub: AwardsBackend = __PREVIEW__
    ? previewAwards
    : {
        wall: () => guildAwards(),
        members: () => listMembers(),
        give: (b) => giveAward(b),
        takeBack: (id) => takeBackAward(id)
      };
  const raidDays = $derived(raidDaysOf(__PREVIEW__ ? previewRaidSession(previewSession.role) : session));
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
      Note, accept or reject each night's applicants, and pick who from the Toads Discord interviews them. Someone
      applying for Sunday meets the Sunday panel in their interview room.
    </p>
    <a class="btn primary" href="{base}/officers/recruitment">Open recruitment</a>
  </section>
{/snippet}

{#snippet calendarLink()}
  <section class="card comp-link" aria-labelledby="calendar-link-h">
    <h2 id="calendar-link-h">Calendar</h2>
    <p class="muted">
      Who will miss your raid nights and why, a few weeks ahead, from the absences members add on their Me page.
    </p>
    <a class="btn primary" href="{base}/officers/calendar/">Open the Calendar</a>
  </section>
{/snippet}

<h1>Officer console</h1>
<p>
  The shared desk every officer uses. Each raid night's own work (its absences, task board and interview panel) is in
  that night's section, which only its officers see.
</p>
<OfficerNights {raidDays} />
{@render calendarLink()}
{@render compLink()}
<ReferenceCard />
{#if globalTier}<AwardsDesk backend={hub} />{/if}

<style>
  .comp-link { display: grid; gap: 0.6rem; justify-items: start; margin-block: 1rem; }
  .comp-link h2, .comp-link p { margin: 0; }
</style>
