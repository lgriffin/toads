<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { raidDaysOf } from '$lib/absences';
  import { previewRaidSession } from '$lib/preview/absences-fake';
  import { previewSession } from '$lib/preview/session.svelte';
  import { previewStrategy } from '$lib/preview/strategy-fake';
  import {
    TITLE_LIMIT,
    URL_LIMIT,
    docProblem,
    hubStrategy,
    pinnedLine,
    strategyError,
    type Library,
    type StrategyDoc
  } from '$lib/strategy';

  // The officers' strategy docs (docs/strategy.md): one pinned Google Doc per raid, which every night running that raid
  // shows on its Raid page. Every officer pins and takes down docs (a night's officers through their night's path, the
  // global tier through /api/admin); each night's officers pick the raid their night is running. The API checks every
  // call.
  let session = $state<Session | null | undefined>(undefined);
  const backend = __PREVIEW__ ? previewStrategy : hubStrategy();
  let library = $state<Library | null>(null);
  let failed = $state(false);
  onMount(async () => {
    if (!__PREVIEW__) session = await getSession().catch(() => null);
    await reload();
  });
  async function reload() {
    try {
      library = await backend.library();
      failed = false;
    } catch {
      failed = library === null;
    }
  }
  const raidDays = $derived(raidDaysOf(__PREVIEW__ ? previewRaidSession(previewSession.role) : session));
  const globalTier = $derived(__PREVIEW__ ? previewSession.role === 'admin' : !!session?.global_officer);
  const runs = (day: string) => globalTier || raidDays.officerDays.includes(day);
  // The night an officer pins through: none for the global tier, else the first night they run.
  const pinDay = $derived(globalTier ? null : (raidDays.officerDays[0] ?? null));
  const canPin = $derived(globalTier || pinDay !== null);

  let raid = $state('');
  let url = $state('');
  let title = $state('');
  let busy = $state(false);
  let problem = $state('');
  let done = $state('');

  async function pin(e: SubmitEvent) {
    e.preventDefault();
    done = '';
    problem = (raid ? '' : 'Pick the raid the doc is for.') || docProblem(url, title) || '';
    if (problem) return;
    busy = true;
    try {
      const doc = await backend.pin(raid, url.trim(), title.trim(), pinDay);
      const short = library?.raids.find((r) => r.raid.id === doc.raid)?.raid.short ?? doc.raid;
      done = `Pinned “${doc.title}” as the ${short} strategy.`;
      [url, title] = ['', ''];
      await reload();
    } catch (err) {
      problem = strategyError(err);
    } finally {
      busy = false;
    }
  }

  async function takeDown(doc: StrategyDoc) {
    if (!confirm(`Take down “${doc.title}”? If it is the pinned doc, the one it replaced is pinned again.`)) return;
    problem = '';
    try {
      await backend.remove(doc.id, pinDay);
    } catch (err) {
      problem = strategyError(err);
    }
    await reload();
  }

  async function choose(day: string, e: Event) {
    const value = (e.currentTarget as HTMLSelectElement).value;
    problem = '';
    try {
      await backend.setNight(day, value || null);
    } catch (err) {
      problem = strategyError(err);
    }
    await reload();
  }
</script>

<svelte:head><title>Strategy · Officers · Toads</title></svelte:head>

<div class="strategy-page">
  <p class="crumb"><a href="{base}/officers/">Officers</a></p>
  <h1>Strategy</h1>
  <p class="lede muted">
    One strategy doc per raid, kept in Google Drive. Pin a new doc and it replaces the raid’s current one everywhere.
    Each night’s Raid page shows the doc for the raid that night is running.
  </p>

  {#if failed}
    <p class="err" role="alert">Could not load the strategy docs; try again later.</p>
  {:else if library === null}
    <p class="muted" role="status">Loading…</p>
  {:else}
    {#if problem}<p class="err" role="alert">{problem}</p>{/if}

    <section class="card" aria-labelledby="nights-h">
      <h2 id="nights-h">What each night is running</h2>
      <p class="muted">A night’s officers pick its raid. Its raiders see that raid’s doc on their Raid page.</p>
      <ul class="nights">
        {#each library.nights as n (n.raid_day)}
          <li>
            <label for="night-{n.raid_day}">{n.name}</label>
            {#if runs(n.raid_day)}
              <select id="night-{n.raid_day}" value={n.raid ?? ''} onchange={(e) => choose(n.raid_day, e)}>
                <option value="">Not decided yet</option>
                {#each library.raids as r (r.raid.id)}
                  <option value={r.raid.id}>{r.raid.short}: {r.raid.name}</option>
                {/each}
              </select>
            {:else}
              <span id="night-{n.raid_day}">
                {library.raids.find((r) => r.raid.id === n.raid)?.raid.name ?? 'Not decided yet'}
              </span>
            {/if}
          </li>
        {/each}
      </ul>
    </section>

    {#if canPin}
      <form class="card pin" onsubmit={pin} aria-labelledby="pin-h">
        <h2 id="pin-h">Pin a strategy doc</h2>
        <div class="fields">
          <label>
            Raid
            <select bind:value={raid} required>
              <option value="" disabled>Pick a raid</option>
              {#each library.raids as r (r.raid.id)}
                <option value={r.raid.id}>{r.raid.short}: {r.raid.name}</option>
              {/each}
            </select>
          </label>
          <label class="wide">
            Google Doc link
            <input
              type="url"
              inputmode="url"
              maxlength={URL_LIMIT}
              placeholder="https://docs.google.com/document/d/…"
              bind:value={url}
              required
            />
          </label>
          <label class="wide">
            <span>Name <span class="muted">(optional)</span></span>
            <input maxlength={TITLE_LIMIT} placeholder="Naxx full clear" bind:value={title} />
          </label>
        </div>
        <p class="muted">Share the doc in Drive with the raiders first; the hub only links it.</p>
        <button class="btn primary" type="submit" disabled={busy}>Pin as the raid’s strategy</button>
        {#if done}<p class="ok" role="status">{done}</p>{/if}
      </form>
    {:else}
      <p class="muted">Officers pin and replace the docs. Ask one when your raid’s doc changes.</p>
    {/if}

    <ul class="raids">
      {#each library.raids as r (r.raid.id)}
        <li class="card">
          <h2>{r.raid.short} <span class="muted">{r.raid.name}</span></h2>
          {#if r.pinned}
            <p class="doc">
              <a href={r.pinned.url} target="_blank" rel="noopener noreferrer">{r.pinned.title}</a>
              <span class="muted">{pinnedLine(r.pinned)}</span>
            </p>
            {#if canPin}
              <button class="btn danger" type="button" onclick={() => r.pinned && takeDown(r.pinned)}>Take down</button>
            {/if}
          {:else}
            <p class="muted">No doc pinned yet.</p>
          {/if}
          {#if r.replaced.length}
            <details>
              <summary>Replaced docs ({r.replaced.length})</summary>
              <ul>
                {#each r.replaced as d (d.id)}
                  <li>
                    <a href={d.url} target="_blank" rel="noopener noreferrer">{d.title}</a>
                    <span class="muted">{pinnedLine(d)}</span>
                    {#if canPin}
                      <button class="btn small danger" type="button" onclick={() => takeDown(d)}>Take down</button>
                    {/if}
                  </li>
                {/each}
              </ul>
            </details>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .strategy-page { font-family: 'Alegreya Sans', system-ui, sans-serif; font-size: 1.05rem; display: grid; gap: 1rem; }
  .strategy-page :global(h2) { font-family: 'Cinzel', Georgia, serif; font-weight: 600; color: var(--bronze-hi); letter-spacing: 0.03em; margin: 0; }
  h1 { font-family: 'Cinzel', Georgia, serif; color: var(--bronze-hi); letter-spacing: 0.04em; margin: 0; }
  .crumb { margin: 0; font-size: 0.95rem; }
  .lede { margin: 0; max-width: 62ch; }
  .card { display: grid; gap: 0.6rem; }
  .card p { margin: 0; }
  .nights { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.5rem; }
  .nights li { display: grid; grid-template-columns: 8rem minmax(0, 1fr); gap: 0.75rem; align-items: center; }
  .nights label { font-weight: 700; }
  .nights select { width: min(100%, 22rem); }
  .fields select, .fields input { width: 100%; box-sizing: border-box; }
  select, input { font: inherit; padding: 0.4rem 0.5rem; border-radius: 6px; max-width: 100%; }
  .fields { display: grid; gap: 0.75rem; grid-template-columns: minmax(0, 14rem) minmax(0, 1fr); }
  .fields label { display: grid; gap: 0.25rem; font-weight: 700; }
  .fields .wide:last-child { grid-column: 2; }
  .pin button { justify-self: start; }
  .ok { color: var(--teal); }
  .raids { list-style: none; margin: 0; padding: 0; display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr)); }
  .raids h2 { font-size: 1.2rem; }
  .raids h2 .muted { font-family: 'Alegreya Sans', system-ui, sans-serif; font-weight: 400; font-size: 1rem; letter-spacing: 0; }
  .raids .btn { justify-self: start; }
  .doc { display: grid; gap: 0.1rem; }
  .doc a { font-weight: 700; overflow-wrap: anywhere; }
  details ul { list-style: none; margin: 0.5rem 0 0; padding: 0; display: grid; gap: 0.4rem; }
  details li { display: flex; flex-wrap: wrap; gap: 0.25rem 0.6rem; align-items: baseline; }
  details a { overflow-wrap: anywhere; }
  @media (max-width: 36rem) {
    .fields { grid-template-columns: 1fr; }
    .fields .wide:last-child { grid-column: auto; }
    .nights li { grid-template-columns: 1fr; gap: 0.25rem; }
  }
</style>
