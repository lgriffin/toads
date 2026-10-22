<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import '$lib/pond.css';
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { dayName, hubAbsences, raidDaysOf, type Absence } from '$lib/absences';
  import { PLANNED, dayToad, defaultDay } from '$lib/raid-page';
  import { NIGHTS_OR } from '$lib/nights';
  import { previewAbsences, previewRaidSession } from '$lib/preview/absences-fake';
  import { previewSession } from '$lib/preview/session.svelte';
  import DaySwitch from '$lib/components/DaySwitch.svelte';
  import NightCrafters from '$lib/components/NightCrafters.svelte';
  import NightStrategy from '$lib/components/NightStrategy.svelte';
  import PondHero from '$lib/components/PondHero.svelte';

  // One raid night's home. Members see their team's night; officers also get the officer desk for the nights they
  // run; super admins see every night and switch between them. The API still checks every call.
  let session = $state<Session | null | undefined>(undefined);
  let mine = $state<Absence[]>([]);
  const backend = __PREVIEW__ ? previewAbsences : hubAbsences;
  onMount(async () => {
    if (!__PREVIEW__) session = await getSession().catch(() => null);
    mine = await backend.mine().catch(() => []);
  });
  const raidDays = $derived(raidDaysOf(__PREVIEW__ ? previewRaidSession(previewSession.role) : session));
  let picked = $state('');
  const day = $derived(raidDays.days.includes(picked) ? picked : defaultDay(raidDays));
  const name = $derived(dayName(day, raidDays.names));
  const officer = $derived(raidDays.officerDays.includes(day));
  const onTeam = $derived(raidDays.teams.includes(day));
  const away = $derived(mine.filter((a) => a.raid_day === day));
  // The bands below the hero alternate dusk and ink: Strategy, the officer desk, nights away, crafters, what's coming.
  const crafterBand = $derived(1 + Number(officer) + Number(onTeam));
  const ready = $derived(__PREVIEW__ ? previewSession.ready : session !== undefined);
</script>

<svelte:head><title>{day ? `${name} raid` : 'Raid'} · Toads</title></svelte:head>

{#if !ready}
  <p class="muted" role="status">Loading…</p>
{:else if !day}
  <section class="card none" aria-labelledby="raid-h">
    <h1 id="raid-h">Raid</h1>
    <p>
      You are not on a raid team yet. Once the officers give you the {NIGHTS_OR} role in Discord, your raid
      night's page opens here.
    </p>
  </section>
{:else}
  <div class="pond-page">
    {#if raidDays.days.length > 1}
      <div class="switch-row">
        <DaySwitch days={raidDays.days} names={raidDays.names} bind:value={() => day, (v) => (picked = v)} />
      </div>
    {/if}

    <PondHero
      title="{name} raid"
      line="Coming soon"
      lede="{name}'s home on the hub. Raid-night tools plug in here as they are built; until then the night runs from Discord and the officers' Drive."
      toads={[dayToad(day, name)]}
    >
      {#if onTeam}<a class="medal" href="{base}/me/#absences">Report an absence</a>{/if}
      <a class="ghost" href="{base}/logs/">See the logs</a>
    </PondHero>

    <NightStrategy {day} {name} {officer} dusk />

    {#if officer}
      <section class="band desk" aria-labelledby="desk-h">
        <div class="head">
          <p class="kicker">Officer desk</p>
          <h2 id="desk-h">Running {name}</h2>
          <p>{name}'s absences, task board and interview panel live in its own officer section.</p>
        </div>
        <a class="medal" href="{base}/officers/nights/{day}/">Open {name}’s officer section</a>
      </section>
    {/if}

    {#if onTeam}
      <section class="band" class:dusk={officer} aria-labelledby="away-h">
        <div class="head">
          <h2 id="away-h">Your nights away</h2>
          {#if away.length}
            <p>
              You have told {name}'s officers about {away.reduce((n, a) => n + a.nights.length, 0)}
              {away.reduce((n, a) => n + a.nights.length, 0) === 1 ? 'night' : 'nights'} you will miss.
              <a href="{base}/me/#absences">Change them on Me.</a>
            </p>
          {:else}
            <p>None booked. If you cannot make a raid, <a href="{base}/me/#absences">add it on Me</a> so the officers can plan the night.</p>
          {/if}
        </div>
      </section>
    {/if}

    <NightCrafters {day} {name} dusk={crafterBand % 2 === 0} />

    <section class="band" class:dusk={crafterBand % 2 === 1} aria-labelledby="soon-h">
      <div class="head">
        <h2 id="soon-h">Coming to the raid page</h2>
        <p>What this page is being built to hold for {name}.</p>
      </div>
      <ul class="planned">
        {#each PLANNED as p (p.title)}
          <li>
            <h3>{p.title}</h3>
            <p>{p.body}</p>
          </li>
        {/each}
      </ul>
    </section>
  </div>
{/if}

<style>
  .none { max-width: 40rem; margin: 2rem auto; }
  .switch-row { padding-top: 1rem; display: grid; }
  .kicker {
    margin: 0;
    font-family: 'Cinzel', Georgia, serif;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    font-size: 0.85rem;
    color: var(--teal);
  }
  .desk .medal { justify-self: start; }
  .planned { list-style: none; margin: 0; padding: 0; display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); }
  .planned li { display: grid; gap: 0.35rem; align-content: start; padding-top: 1rem; border-top: 2px solid var(--bronze); }
  .planned p { margin: 0; color: var(--muted); }
</style>
