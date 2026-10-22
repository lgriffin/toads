<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import '$lib/pond.css';
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { dayName, hubAbsences, raidDaysOf } from '$lib/absences';
  import { hubPanels } from '$lib/interview-panels';
  import { hubComps } from '$lib/comp';
  import { hubLinks } from '$lib/night-links';
  import { hubBoard } from '$lib/officer-board';
  import { hubClaims } from '$lib/officer-claims';
  import { dayToad } from '$lib/raid-page';
  import { previewAbsences, previewRaidSession } from '$lib/preview/absences-fake';
  import { previewBoard } from '$lib/preview/board-fake';
  import { previewClaims } from '$lib/preview/claims-fake';
  import { previewComps } from '$lib/preview/comp-fake';
  import { previewLinks } from '$lib/preview/links-fake';
  import { previewPanels } from '$lib/preview/panels-fake';
  import { previewSession } from '$lib/preview/session.svelte';
  import ClaimsQueue from '$lib/components/ClaimsQueue.svelte';
  import NightTonight from '$lib/components/NightTonight.svelte';
  import InterviewPanelCard from '$lib/components/InterviewPanelCard.svelte';
  import OfficerBoard from '$lib/components/OfficerBoard.svelte';
  import PondHero from '$lib/components/PondHero.svelte';
  import TeamAbsences from '$lib/components/TeamAbsences.svelte';

  // One raid night's own officer section: tonight at a glance (who is away, the pinned Drive documents), its members' character claims, its team's absences, its task board and its interview panel. Only that
  // night's officers see it (global officers and super admins see every night); another night's officers get a
  // refusal and none of its content. The API checks every call against the night in the path. Keyed by night, so
  // moving to another night's section starts its panels afresh rather than showing the last night's.
  let { data }: { data: { day: string } } = $props();
  let session = $state<Session | null | undefined>(undefined);
  onMount(async () => {
    if (!__PREVIEW__) session = await getSession().catch(() => null);
  });
  const raidDays = $derived(raidDaysOf(__PREVIEW__ ? previewRaidSession(previewSession.role) : session));
  const ready = $derived(__PREVIEW__ ? previewSession.ready : session !== undefined);
  const day = $derived(data.day);
  const name = $derived(dayName(day, raidDays.names));
  const runs = $derived(raidDays.officerDays.includes(day));
  const absences = __PREVIEW__ ? previewAbsences : hubAbsences;
  const board = __PREVIEW__ ? previewBoard : hubBoard();
  const panels = __PREVIEW__ ? previewPanels() : hubPanels();
  const claims = __PREVIEW__ ? previewClaims : hubClaims();
  const comps = __PREVIEW__ ? previewComps : hubComps();
  const links = __PREVIEW__ ? previewLinks : hubLinks();
</script>

<svelte:head><title>{runs ? `${name} officers` : 'Officers'} · Toads</title></svelte:head>

{#if !ready}
  <p class="muted" role="status">Loading…</p>
{:else if !runs}
  <section class="card none" aria-labelledby="none-h">
    <h1 id="none-h">Officers</h1>
    <p>This is another raid night's officer section, for its own officers. Yours are on the <a href="{base}/officers/">Officer console</a>.</p>
  </section>
{:else}
  {#key day}
  <div class="pond-page">
    <PondHero
      title="{name} officers"
      line="Your night's officer section"
      lede="Everything {name}'s officers run for their own team: character claims, who is away, the task board and the interview panel. Only {name}'s officers and super admins see it."
      toads={[dayToad(day, name)]}
    >
      <a class="medal" href="{base}/officers/comp?day={day}">Build {name}'s comp</a>
      <a class="ghost" href="{base}/officers/">Officer console</a>
    </PondHero>

    <NightTonight {day} {name} {absences} {comps} {links} />

    <div class="band"><ClaimsQueue backend={claims} {day} title="Character claims" names={raidDays.names} /></div>

    <section class="band dusk" aria-labelledby="away-h">
      <div class="head">
        <h2 id="away-h">Every absence ahead</h2>
        <p>Everyone on {name} who has said they will miss a night after this one too, with their note.</p>
      </div>
      <div class="card"><TeamAbsences backend={absences} {day} {name} heading={false} /></div>
    </section>

    <div class="band"><OfficerBoard backend={board} {day} dayName={name} /></div>

    <div class="band dusk"><InterviewPanelCard backend={panels} {day} night={name} /></div>
  </div>
  {/key}
{/if}

<style>
  .none { max-width: 40rem; margin: 2rem auto; }
  .none h1 { margin-top: 0; }
  .card { padding: 1.25rem; }
</style>
