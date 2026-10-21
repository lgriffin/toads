<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { ApiError, getSession, myBadges, type Session } from '$lib/api';
  import { hubAbsences, raidDaysOf } from '$lib/absences';
  import { absencesOnly } from '$lib/launch';
  import { previewAbsences, previewRaidSession } from '$lib/preview/absences-fake';
  import { previewSession } from '$lib/preview/session.svelte';
  import AbsenceCalendar from '$lib/components/AbsenceCalendar.svelte';
  import type { MyBadges } from '$lib/badges';
  import { myAwards, titlesOf, type AwardOut } from '$lib/awards';
  import AwardsCard from '$lib/components/AwardsCard.svelte';
  import BadgesCard from '$lib/components/BadgesCard.svelte';
  import CharacterCard from '$lib/components/CharacterCard.svelte';
  import MainSwap from '$lib/components/MainSwap.svelte';
  import { hubMain } from '$lib/main-swap';
  import { myCharacterPage, type MyCharacterPage } from '$lib/characters';
  import MemberToads from '$lib/components/MemberToads.svelte';
  import SpecsCard from '$lib/components/SpecsCard.svelte';
  import ProfessionsCard from '$lib/components/ProfessionsCard.svelte';
  import { previewMyProfessions } from '$lib/preview/professions-fake';
  import { getMe } from '$lib/me-context';
  import { previewAwardsOf } from '$lib/preview/awards-fake';
  import { previewMain } from '$lib/preview/main-fake';
  import { previewBadges } from '$lib/mock/badges';
  import { previewCharacterPage } from '$lib/mock/characters';
  import { memberToads } from '$lib/toads';

  type Loaded = { kind: 'loading' } | { kind: 'ok'; value: MyBadges } | { kind: 'error'; message: string };
  let badges = $state<Loaded>({ kind: 'loading' });
  let awards = $state<AwardOut[] | null>(null);
  type Raids = { kind: 'loading' } | { kind: 'ok'; value: MyCharacterPage } | { kind: 'error'; message: string };
  let raids = $state<Raids>({ kind: 'loading' });
  // A failed switch to another character: the shown page stays, with this message beside it.
  let switchError = $state('');
  let latest = 0;
  const mains = __PREVIEW__ ? previewMain : hubMain();

  // The member's main character first; `pick` loads another of theirs, keeping the current page until it arrives.
  // Only the latest request lands, so quick switches never end on an earlier character.
  async function loadRaids(name: string | null = null) {
    const request = ++latest;
    switchError = '';
    if (__PREVIEW__) {
      raids = { kind: 'ok', value: previewCharacterPage(name) };
      return;
    }
    try {
      const value = await myCharacterPage(name);
      if (request === latest) raids = { kind: 'ok', value };
    } catch (e) {
      if (request !== latest) return;
      const message =
        e instanceof ApiError && e.status === 401
          ? 'Sign in with Discord to see your raids.'
          : 'Could not load your raids; try again later.';
      if (name && raids.kind === 'ok') switchError = message;
      else raids = { kind: 'error', message };
    }
  }
  // The same toads the header shows beside the member's name, loaded once by the layout; the titles come from the
  // awards fetched here, so an award given since the layout loaded shows too.
  const me = getMe();
  const facts = $derived(awards ? { ...me(), titles: titlesOf(awards) } : me());
  const toads = $derived(memberToads(facts));

  // Absences: the member's raid nights and the ones they will miss, each with a note; their officers see them under
  // Officers. During the launch hold a raider's Me holds only this, since the rest is the held Logs analysis.
  let session = $state<Session | null | undefined>(undefined);
  const absences = __PREVIEW__ ? previewAbsences : hubAbsences;
  const raidDays = $derived(raidDaysOf(__PREVIEW__ ? previewRaidSession(previewSession.role) : session));
  const absencesReady = $derived(__PREVIEW__ ? previewSession.ready : session !== undefined);
  const held = $derived(absencesOnly(me().tier ?? 'visitor'));

  // Every failure lands in the page as a message; nothing here throws to the error page.
  onMount(async () => {
    if (__PREVIEW__) {
      // The preview is this same page, answered from sample data in the browser.
      awards = previewAwardsOf(1);
      badges = { kind: 'ok', value: previewBadges };
      void loadRaids();
      return;
    }
    getSession()
      .then((s) => (session = s))
      .catch(() => (session = null));
    myAwards()
      .then((a) => (awards = a))
      .catch(() => (awards = []));
    void loadRaids();
    try {
      badges = { kind: 'ok', value: await myBadges() };
    } catch (e) {
      const message =
        e instanceof ApiError && e.status === 401
          ? 'Sign in with Discord to see your badges.'
          : 'Could not load your badges; try again later.';
      badges = { kind: 'error', message };
    }
  });
</script>

{#snippet absenceSection()}
  <section class="absences" id="absences" aria-labelledby="absences-h">
    <h2 id="absences-h">Your absences</h2>
    <p class="muted">
      Add the raid nights you cannot make, with a note for the officers, and change or delete them here. That night's
      officers see them ahead of the raid.
    </p>
    {#if absencesReady}
      <AbsenceCalendar backend={absences} {raidDays} />
    {:else}
      <p class="muted" role="status">Loading…</p>
    {/if}
  </section>
{/snippet}

{#if held}
  <h1>Me</h1>
  <p>Your numbers, badges and characters arrive with the hub at launch. Until then, keep your officers posted here.</p>
  {@render absenceSection()}
{:else}
  <h1>Me <MemberToads {...facts} size={40} /></h1>
  <!-- Four parts, in the order a raider reaches for them: how the last raids went, the nights they will miss, the specs and
       professions officers plan around, and the badges and toads they have earned. -->
  <nav class="jump" aria-label="On this page">
    <a href="#raids">Your raids</a>
    <a href="#absences">Absences</a>
    <a href="#specs">Characters, specs and professions</a>
    <a href="#badges">Badges and toads</a>
  </nav>

  <div class="part" id="raids">
    {#if raids.kind === 'ok'}
      {@const shown = raids.value.characters}
      <CharacterCard mine={raids.value} pick={(name) => loadRaids(name)}>
        {#snippet main(viewing)}<MainSwap backend={mains} {viewing} {shown} />{/snippet}
      </CharacterCard>
      {#if switchError}<p class="err" role="alert">{switchError}</p>{/if}
    {:else}
      <section class="card" aria-labelledby="character-h">
        <h2 id="character-h">Your raids</h2>
        {#if raids.kind === 'loading'}
          <p class="muted" role="status">Loading…</p>
        {:else}
          <p class="err" role="alert">{raids.message}</p>
        {/if}
      </section>
    {/if}
  </div>

  {@render absenceSection()}

  <div class="part" id="specs">
    <SpecsCard />
    <ProfessionsCard preview={__PREVIEW__ ? previewMyProfessions : null} />
    <p class="links">
      <a href="{base}/setup">Your setup: main, specs and alts</a> · <a href="{base}/me/claim">Claim your characters</a> · <a href="{base}/me/settings">Your name and Warcraft Logs key</a>
    </p>
  </div>

  <div class="part" id="badges">
    {#if badges.kind === 'ok'}
      <BadgesCard mine={badges.value} />
    {:else}
      <section class="card" aria-labelledby="badges-h">
        <h2 id="badges-h">Your badges</h2>
        {#if badges.kind === 'loading'}
          <p class="muted" role="status">Loading…</p>
        {:else}
          <p class="err" role="alert">{badges.message}</p>
        {/if}
      </section>
    {/if}
    {#if awards}<AwardsCard {awards} {toads} />{/if}
  </div>
{/if}

<style>
  .jump { display: flex; flex-wrap: wrap; gap: 0.25rem 1.25rem; margin: 0 0 1rem; }
  .jump a { display: inline-flex; align-items: center; min-height: 2.75rem; }
  .part { display: grid; grid-template-columns: minmax(0, 1fr); gap: 1rem; margin-block: 1rem; scroll-margin-top: 4.5rem; }
  .links { margin: 0; }
  .absences { display: grid; gap: 0.75rem; margin-block: 1rem; scroll-margin-top: 4.5rem; }
  .absences h2, .absences > p { margin: 0; }
</style>
