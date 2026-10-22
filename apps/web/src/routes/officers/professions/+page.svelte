<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { dayName, raidDaysOf } from '$lib/absences';
  import { crafterGroups, describe, hubProfessions, type Crafter } from '$lib/professions';
  import { previewRaidSession } from '$lib/preview/absences-fake';
  import { previewProfessions } from '$lib/preview/professions-fake';
  import { previewSession } from '$lib/preview/session.svelte';
  import ProfessionsRoster from '$lib/components/ProfessionsRoster.svelte';

  // The officers' view of members' professions: one panel for each raid night the viewer runs, and for global officers
  // and super admins one more with everyone who lists a profession. Above them, the guild's crafters, guild-wide: the
  // members officers named as the people to send top end recipes to. The API refuses anyone who is not that night's
  // officer.
  let session = $state<Session | null | undefined>(undefined);
  const backend = __PREVIEW__ ? previewProfessions() : hubProfessions();
  onMount(async () => {
    if (!__PREVIEW__) session = await getSession().catch(() => null);
  });
  const raidDays = $derived(raidDaysOf(__PREVIEW__ ? previewRaidSession(previewSession.role) : session));
  const ready = $derived(__PREVIEW__ ? previewSession.ready : session !== undefined);
  const globalTier = $derived(__PREVIEW__ ? previewSession.role === 'admin' : !!session?.global_officer);
  let crafters = $state<Crafter[] | null>(null);
  let crafterError = $state(false);
  // Bumped after any naming, so every panel reloads: the naming is guild-wide.
  let revision = $state(0);
  const panel = {
    oncrafters: (c: Crafter[]) => ([crafters, crafterError] = [c, false]),
    onfailed: () => (crafterError = crafters === null),
    onchanged: () => revision++
  };
  const groups = $derived(crafters ? crafterGroups(crafters) : []);
</script>

<svelte:head><title>Professions · Officers · Toads</title></svelte:head>

<div class="professions-page">
  <p class="crumb"><a href="{base}/officers/">Officers</a></p>
  <h1>Professions</h1>
  <p class="lede muted">
    Members pick their professions on Me. Name the guild’s crafters here: the people we send top end recipes to. A night’s
    officers name members of their night; global officers name anyone.
  </p>

  {#if !ready}
    <p class="muted" role="status">Loading…</p>
  {:else if !raidDays.officerDays.length && !globalTier}
    <section class="card">
      <p>Professions are shown to a raid night’s officers. You do not run a raid night, so there is nothing to show here.</p>
    </section>
  {:else}
    <section class="card crafters" aria-labelledby="crafters-h">
      <h2 id="crafters-h">Guild crafters</h2>
      {#if crafters === null && crafterError}
        <p class="err" role="alert">Could not load the guild’s crafters; try again later.</p>
      {:else if crafters === null}
        <p class="muted" role="status">Loading…</p>
      {:else if !groups.length}
        <p class="muted">Nobody is named yet. Pick a member’s profession below and name them.</p>
      {:else}
        <dl>
          {#each groups as g (g.profession.id)}
            <dt>{g.profession.name}</dt>
            <dd>
              <ul>
                {#each g.crafters as c (c.member_id)}
                  <li>
                    <strong>{c.member_name}</strong>
                    <span class="muted">{describe(c).slice(g.profession.name.length).trim()}</span>
                    {#if c.note}<span> · {c.note}</span>{/if}
                  </li>
                {/each}
              </ul>
            </dd>
          {/each}
        </dl>
      {/if}
    </section>

    <div class="nights">
      {#each raidDays.officerDays as day (day)}
        <ProfessionsRoster {backend} {day} title="{dayName(day, raidDays.names)} professions" {revision} {...panel} />
      {/each}
      {#if globalTier}
        <ProfessionsRoster {backend} day={null} title="Everyone who lists a profession" {revision} {...panel} />
      {/if}
    </div>
  {/if}
</div>

<style>
  .professions-page { font-family: 'Alegreya Sans', system-ui, sans-serif; font-size: 1.05rem; }
  .professions-page :global(h2) { font-family: 'Cinzel', Georgia, serif; font-weight: 600; color: var(--bronze-hi); letter-spacing: 0.03em; }
  h1 { font-family: 'Cinzel', Georgia, serif; color: var(--bronze-hi); letter-spacing: 0.04em; }
  .crumb { margin: 0 0 0.25rem; font-size: 0.95rem; }
  .lede { margin: -0.5rem 0 1.25rem; max-width: 62ch; }
  .crafters { display: grid; gap: 0.6rem; margin-bottom: 1rem; }
  .crafters h2 { margin: 0; }
  dl { margin: 0; display: grid; grid-template-columns: max-content 1fr; gap: 0.4rem 1.25rem; }
  dt { font-weight: 700; }
  dd { margin: 0; }
  dd ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.2rem; }
  @media (max-width: 30rem) { dl { grid-template-columns: 1fr; } dd { margin-bottom: 0.4rem; } }
  .nights { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr)); }
</style>
