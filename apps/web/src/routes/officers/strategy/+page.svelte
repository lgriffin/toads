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
  import DocPicker from '$lib/components/DocPicker.svelte';
  import {
    TITLE_LIMIT,
    URL_LIMIT,
    addedLine,
    docOptions,
    docProblem,
    hubStrategy,
    strategyError,
    type LibraryDoc,
    type Library
  } from '$lib/strategy';

  // The officers' strategy docs (docs/strategy.md): every officer adds Google Docs to each raid here (a night's officers
  // through their night's path, the global tier through /api/admin); each night's officers then pin the docs its
  // raiders see, here or on the night's Raid page. The API checks every call.
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
      // The first load failing leaves nothing to show; a later refresh failing leaves the last list up, marked stale.
      failed = library === null;
      if (library !== null) listProblem ||= 'Could not refresh the strategy docs; what is shown may be out of date.';
    }
  }
  const raidDays = $derived(raidDaysOf(__PREVIEW__ ? previewRaidSession(previewSession.role) : session));
  const globalTier = $derived(__PREVIEW__ ? previewSession.role === 'admin' : !!session?.global_officer);
  const runs = (day: string) => globalTier || raidDays.officerDays.includes(day);
  const canAdd = $derived(globalTier || raidDays.officerDays.length > 0);
  // The night a night officer acts through: the first night they run; none for the global tier.
  const through = $derived(globalTier ? null : (raidDays.officerDays[0] ?? null));
  // A night's officers take down a doc only no other night pins; the global tier any.
  const canTakeDown = (doc: LibraryDoc) => canAdd && (globalTier || doc.nights.every((n) => runs(n)));
  const nightName = (day: string) => library?.nights.find((n) => n.raid_day === day)?.name ?? day;
  const options = $derived(library ? docOptions(library) : []);

  let raid = $state('');
  let url = $state('');
  let title = $state('');
  let busy = $state(false);
  let addProblem = $state('');
  let done = $state('');
  let nightProblem = $state('');
  let listProblem = $state('');

  async function add(e: SubmitEvent) {
    e.preventDefault();
    done = '';
    addProblem = (raid ? '' : 'Pick the raid the doc is for.') || docProblem(url, title) || '';
    if (addProblem) return;
    busy = true;
    try {
      const doc = await backend.add(raid, url.trim(), title.trim(), through);
      const short = library?.raids.find((r) => r.raid.id === doc.raid)?.raid.short ?? doc.raid;
      done = `Added “${doc.title}” to ${short}. Pin it for a night below, or on the night’s Raid page.`;
      [url, title] = ['', ''];
      await reload();
    } catch (err) {
      addProblem = strategyError(err);
    } finally {
      busy = false;
    }
  }

  async function takeDown(doc: LibraryDoc) {
    const pinned = doc.nights.length ? ` It comes off ${doc.nights.map(nightName).join(' and ')}’s Raid page.` : '';
    if (!confirm(`Take down “${doc.title}”?${pinned}`)) return;
    listProblem = '';
    try {
      await backend.remove(doc.id, globalTier ? null : (doc.nights[0] ?? through));
    } catch (err) {
      listProblem = strategyError(err);
    }
    await reload();
  }

  // The night whose docs are saving: its picker waits, so a second tick builds on the first one's answer.
  let savingNight = $state<string | null>(null);
  async function pin(day: string, picked: string[]): Promise<boolean> {
    nightProblem = '';
    savingNight = day;
    try {
      await backend.setNight(day, picked.map(Number));
      return true;
    } catch (err) {
      nightProblem = strategyError(err);
      return false;
    } finally {
      await reload();
      savingNight = null;
    }
  }
</script>

<svelte:head><title>Strategy · Officers · Toads</title></svelte:head>

<div class="strategy-page">
  <p class="crumb"><a href="{base}/officers/">Officers</a></p>
  <h1>Strategy</h1>
  <p class="lede muted">
    Strategy docs live in Google Drive. Add each raid’s docs here, then pin the ones raiders need for a night, below or
    on that night’s Raid page. Raiders only see the docs their night pins.
  </p>

  {#if failed}
    <p class="err" role="alert">Could not load the strategy docs; try again later.</p>
  {:else if library === null}
    <p class="muted" role="status">Loading…</p>
  {:else}
    {#if canAdd}
      <form class="card add" onsubmit={add} aria-labelledby="add-h">
        <h2 id="add-h">Add a doc to a raid</h2>
        <div class="fields">
          <label>
            Raid
            <select bind:value={raid}>
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
            />
          </label>
          <label class="wide">
            <span>Name <span class="muted">(optional)</span></span>
            <input maxlength={TITLE_LIMIT} placeholder="Naxx full clear" bind:value={title} />
          </label>
        </div>
        <p class="muted">Share the doc in Drive with the raiders first; the hub only links it.</p>
        <button class="btn primary" type="submit" disabled={busy}>Add the doc</button>
        {#if addProblem}<p class="err" role="alert">{addProblem}</p>{/if}
        {#if done}<p class="ok" role="status">{done}</p>{/if}
      </form>
    {:else}
      <p class="muted">Officers add and pin the docs. Ask one when your raid’s doc changes.</p>
    {/if}

    <section class="card" aria-labelledby="nights-h">
      <h2 id="nights-h">What each night’s raiders see</h2>
      <p class="muted">A night’s officers pin one or more docs, one per raid the night runs or more. Raiders see them on their Raid page.</p>
      <ul class="nights">
        {#each library.nights as n (n.raid_day)}
          <li>
            <span class="night-name">{n.name}</span>
            {#if runs(n.raid_day)}
              <DocPicker
                label="Docs pinned for {n.name}"
                {options}
                chosen={n.docs.map(String)}
                disabled={savingNight === n.raid_day}
                onchange={(picked) => pin(n.raid_day, picked)}
              />
            {:else}
              <span>
                {n.docs
                  .flatMap((id) => options.filter((o) => o.id === String(id)))
                  .map((o) => `${o.short}: ${o.name}`)
                  .join(', ') || 'No docs pinned'}
              </span>
            {/if}
          </li>
        {/each}
      </ul>
      {#if nightProblem}<p class="err" role="alert">{nightProblem}</p>{/if}
    </section>

    {#if listProblem}<p class="err" role="alert">{listProblem}</p>{/if}
    <ul class="raids">
      {#each library.raids as r (r.raid.id)}
        <li class="card">
          <h2>{r.raid.short} <span class="muted">{r.raid.name}</span></h2>
          {#if r.docs.length}
            <ul class="docs" aria-label="{r.raid.short} docs">
              {#each r.docs as d (d.id)}
                <li class="doc">
                  <a href={d.url} target="_blank" rel="noopener noreferrer">{d.title}</a>
                  <span class="muted">{addedLine(d)}</span>
                  <span class="pins" class:on={d.nights.length}>
                    {d.nights.length ? `Pinned for ${d.nights.map(nightName).join(', ')}` : 'Not pinned for any night'}
                  </span>
                  {#if canTakeDown(d)}
                    <button class="btn small danger" type="button" onclick={() => takeDown(d)}>Take down</button>
                  {/if}
                </li>
              {/each}
            </ul>
          {:else}
            <p class="muted">No docs added yet.</p>
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
  .nights li { display: grid; grid-template-columns: 8rem minmax(0, 1fr); gap: 0.75rem; align-items: start; }
  .night-name { font-weight: 700; padding-top: 0.4rem; }
  .nights :global(.picker) { justify-self: start; }
  .nights li > span:not(.night-name) { padding-top: 0.4rem; }
  .fields select, .fields input { width: 100%; box-sizing: border-box; }
  select, input { font: inherit; padding: 0.4rem 0.5rem; border-radius: 6px; max-width: 100%; }
  .fields { display: grid; gap: 0.75rem; grid-template-columns: minmax(0, 14rem) minmax(0, 1fr); }
  .fields label { display: grid; gap: 0.25rem; font-weight: 700; }
  .fields .wide:last-child { grid-column: 2; }
  .add button { justify-self: start; }
  .ok { color: var(--teal); }
  .raids { list-style: none; margin: 0; padding: 0; display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr)); }
  .raids h2 { font-size: 1.2rem; }
  .raids { align-items: start; }
  .raids .card { align-content: start; }
  .raids h2 .muted { font-family: 'Alegreya Sans', system-ui, sans-serif; font-weight: 400; font-size: 1rem; letter-spacing: 0; }
  .raids .btn { justify-self: start; }
  .docs { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.6rem; }
  .doc { display: grid; gap: 0.15rem; padding-top: 0.6rem; border-top: 1px solid var(--line); }
  .doc a { font-weight: 700; overflow-wrap: anywhere; }
  .doc .pins { font-size: 0.95rem; }
  .doc .pins.on { color: var(--teal); }
  .doc .btn { margin-top: 0.25rem; }
  @media (max-width: 36rem) {
    .fields { grid-template-columns: 1fr; }
    .fields .wide:last-child { grid-column: auto; }
    .nights li { grid-template-columns: 1fr; gap: 0.25rem; }
  }
</style>
