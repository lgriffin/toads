<script lang="ts">
  import { PROVIDER_LABELS } from '$lib/clips';
  import type { Application, Visibility } from '$lib/community';
  import ClipPlayer from '$lib/components/ClipPlayer.svelte';
  import { MOCK_NOW, type RaidDay } from '$lib/mock/data';
  import { shortDate } from '$lib/format';
  import { viewer } from '$lib/mock/community';
  import { POST_LIMITS, validatePost, type PostErrors } from '$lib/posts';
  import {
    APPLICATION_STATUSES,
    STATUS_LABELS,
    canTransition,
    isFinal,
    nextActions,
    type ApplicationStatus
  } from '$lib/recruitment';
  import { community } from './state.svelte';

  // Preview: every action below changes in-memory state only. The API is the real gate on each of them.
  const SECTIONS = [
    { id: 'applications', label: 'Applications' },
    { id: 'curation', label: 'Discord curation' },
    { id: 'compose', label: 'Compose post' },
    { id: 'highlights', label: 'Highlights review' },
    { id: 'spotlights', label: 'Spotlights' }
  ];

  let tick = 0;
  function now(): string {
    // Stable, increasing timestamps after the mock "now" so the preview is deterministic.
    tick += 1;
    return new Date(MOCK_NOW.getTime() + tick * 60_000).toISOString();
  }

  // --- Applications
  const byStatus = $derived(
    APPLICATION_STATUSES.map((status) => ({
      status,
      apps: community.applications.filter((a) => a.status === status)
    })).filter((g) => g.apps.length)
  );
  let appNote = $state('');

  function roomName(a: Application): string {
    const slug = a.characterName
      .normalize('NFD')
      .replace(/[^A-Za-z]/g, '')
      .toLowerCase();
    return `interview-${slug || a.id}`;
  }

  function move(a: Application, to: ApplicationStatus) {
    if (!canTransition(a.status, to)) return;
    let note = '';
    if (to === 'interviewing' && !a.interviewChannelId) {
      a.interviewChannelId = roomName(a);
      note = `Opened #${a.interviewChannelId}`;
    } else if (isFinal(to) && a.interviewChannelId) {
      note = 'Room locked';
    }
    a.events.push({ at: now(), actorName: viewer.name, from: a.status, to, note });
    a.status = to;
    appNote = `${a.characterName} is now ${STATUS_LABELS[to].toLowerCase()}.`;
  }

  // --- Curation queue
  const queue = $derived(community.posts.filter((p) => p.status === 'pending_review'));
  let curateNote = $state('');
  function curate(id: string, action: 'guild' | 'public' | 'hide') {
    const p = community.posts.find((x) => x.id === id);
    if (!p) return;
    if (action === 'hide') {
      p.status = 'hidden';
      curateNote = `Hid “${p.title}”.`;
    } else {
      p.visibility = action;
      p.raidDay = null;
      p.status = 'published';
      p.publishedAt = now();
      p.editedSinceReview = false;
      curateNote = `Published “${p.title}” to ${action === 'public' ? 'the public story' : 'the guild'}.`;
    }
  }

  // --- Compose
  const officerDays: RaidDay[] = viewer.globalOfficer ? ['Wednesday', 'Sunday'] : viewer.officerDays;
  let draft = $state({ title: '', body: '', visibility: 'guild' as Visibility, raidDay: officerDays[0] ?? null, toDiscord: true });
  let postErrors = $state<PostErrors>({});
  let composeNote = $state('');
  function compose(e: SubmitEvent) {
    e.preventDefault();
    const raidDay = draft.visibility === 'raid_day' ? draft.raidDay : null;
    postErrors = validatePost({ ...draft, raidDay }, viewer.officerDays, viewer.globalOfficer);
    if (Object.keys(postErrors).length) return;
    const at = now();
    community.posts.unshift({
      id: `p-local-${at}`,
      title: draft.title.trim(),
      body: draft.body.trim(),
      authorName: viewer.name,
      origin: 'hub',
      visibility: draft.visibility,
      raidDay,
      status: 'published',
      pinned: false,
      publishToDiscord: draft.toDiscord,
      discordMessageId: null,
      editedSinceReview: false,
      createdAt: at,
      publishedAt: at
    });
    composeNote = `Posted “${draft.title.trim()}”${draft.toDiscord ? ' and queued it for Discord' : ''}.`;
    draft.title = '';
    draft.body = '';
  }

  // --- Highlights
  const submitted = $derived(community.highlights.filter((h) => h.status === 'submitted'));
  let hlNote = $state('');
  function review(id: string, action: 'public' | 'guild' | 'reject') {
    const h = community.highlights.find((x) => x.id === id);
    if (!h) return;
    if (action === 'reject') h.status = 'rejected';
    else {
      h.status = 'published';
      h.visibility = action;
    }
    hlNote = `${action === 'reject' ? 'Rejected' : 'Published'} “${h.title}”.`;
  }

  // --- Spotlights
  const CONSENT_LABELS = { pending: 'Consent pending', granted: 'Consent granted', declined: 'Consent declined' };
  let spotNote = $state('');
  function setSpotlight(id: string, status: 'published' | 'retired') {
    const s = community.spotlights.find((x) => x.id === id);
    if (!s) return;
    if (status === 'published' && s.consent !== 'granted') return;
    s.status = status;
    spotNote = `${status === 'published' ? 'Published' : 'Retired'} the spotlight on ${s.characterName}.`;
  }
</script>

<h1>Officer console</h1>
<nav class="sections" aria-label="Officer sections">
  {#each SECTIONS as s}<a href="#{s.id}">{s.label}</a>{/each}
</nav>

<section id="applications" class="card" aria-labelledby="applications-h">
  <h2 id="applications-h">Applications</h2>
  <p class="sr-only" role="status">{appNote}</p>
  {#each byStatus as group (group.status)}
    <h3 class="group">{STATUS_LABELS[group.status]} <span class="muted">({group.apps.length})</span></h3>
    <div class="cards">
      {#each group.apps as a (a.id)}
        <article class="app" data-testid="application-{a.id}">
          <header class="app-head">
            <h4>{a.characterName}</h4>
            <span class="pill status-{a.status}">{STATUS_LABELS[a.status]}</span>
            {#if a.interviewChannelId}
              <span class="pill room">{isFinal(a.status) ? 'Interview room locked' : 'Interview room open'}</span>
            {/if}
          </header>
          <p class="muted">
            {a.spec}
            {a.className} · {a.role} · {a.raidDays.length ? a.raidDays.join(' & ') : 'Either night'} · applicant {a.applicantName}
          </p>
          <dl>
            <dt>Experience</dt>
            <dd class="text">{a.experience || '—'}</dd>
            <dt>Availability</dt>
            <dd class="text">{a.availability || '—'}</dd>
            {#if a.logsUrl}
              <dt>Logs</dt>
              <dd><a href={a.logsUrl} target="_blank" rel="noopener noreferrer">Warcraft Logs</a></dd>
            {/if}
            {#if a.interviewChannelId}
              <dt>Room</dt>
              <dd>#{a.interviewChannelId}</dd>
            {/if}
          </dl>
          <details>
            <summary>History ({a.events.length})</summary>
            <ol class="events">
              {#each a.events as ev}
                <li>
                  <span class="muted">{shortDate(ev.at)}</span>
                  {ev.actorName}: {ev.from ? `${STATUS_LABELS[ev.from]} → ` : ''}{STATUS_LABELS[ev.to]}{ev.note ? ` · ${ev.note}` : ''}
                </li>
              {/each}
            </ol>
          </details>
          {#if !isFinal(a.status)}
            <div class="actions">
              {#each nextActions(a.status) as act (act.to)}
                <button
                  type="button"
                  class="btn"
                  class:primary={act.tone === 'primary'}
                  class:danger={act.tone === 'danger'}
                  onclick={() => move(a, act.to)}
                  aria-label="{act.label}: {a.characterName}">{act.label}</button
                >
              {/each}
            </div>
          {/if}
        </article>
      {/each}
    </div>
  {/each}
</section>

<section id="curation" class="card" aria-labelledby="curation-h">
  <h2 id="curation-h">Discord curation queue</h2>
  <p class="muted">Messages from the Discord channels the hub mirrors. Nothing reaches the hub until an officer publishes it.</p>
  {#if curateNote}<p role="status">{curateNote}</p>{/if}
  {#each queue as p (p.id)}
    <article class="queued">
      <header class="app-head">
        <h3>{p.title}</h3>
        <span class="pill">from Discord</span>
        {#if p.editedSinceReview}<span class="pill edited">Edited since review</span>{/if}
      </header>
      <p class="text">{p.body}</p>
      <p class="muted small">{p.authorName} · {shortDate(p.createdAt)}</p>
      <div class="actions">
        <button type="button" class="btn primary" onclick={() => curate(p.id, 'guild')}>Publish to guild</button>
        <button type="button" class="btn" onclick={() => curate(p.id, 'public')}>Publish public</button>
        <button type="button" class="btn danger" onclick={() => curate(p.id, 'hide')}>Hide</button>
      </div>
    </article>
  {:else}
    <p class="muted">Queue is empty.</p>
  {/each}
</section>

<section id="compose" class="card" aria-labelledby="compose-h">
  <h2 id="compose-h">Compose post</h2>
  <form novalidate onsubmit={compose}>
    <div class="field">
      <label for="c-title">Title</label>
      <input
        id="c-title"
        bind:value={draft.title}
        aria-invalid={postErrors.title ? 'true' : undefined}
        aria-describedby="c-title-count{postErrors.title ? ' c-title-err' : ''}"
      />
      <span id="c-title-count" class="hint" class:over={draft.title.length > POST_LIMITS.title}
        >{draft.title.length}/{POST_LIMITS.title}</span
      >
      {#if postErrors.title}<span id="c-title-err" class="err">{postErrors.title}</span>{/if}
    </div>
    <div class="field">
      <label for="c-body">Body</label>
      <textarea
        id="c-body"
        rows="5"
        bind:value={draft.body}
        aria-invalid={postErrors.body ? 'true' : undefined}
        aria-describedby="c-body-count{postErrors.body ? ' c-body-err' : ''}"
      ></textarea>
      <span id="c-body-count" class="hint" class:over={draft.body.length > POST_LIMITS.body}
        >{draft.body.length}/{POST_LIMITS.body} · plain text, line breaks kept</span
      >
      {#if postErrors.body}<span id="c-body-err" class="err">{postErrors.body}</span>{/if}
    </div>
    <div class="row">
      <div class="field">
        <label for="c-aud">Audience</label>
        <select id="c-aud" bind:value={draft.visibility}>
          <option value="public">Public story</option>
          <option value="guild">Guild</option>
          <option value="raid_day">One raid day</option>
        </select>
      </div>
      {#if draft.visibility === 'raid_day'}
        <div class="field">
          <label for="c-day">Raid day</label>
          <select
            id="c-day"
            bind:value={draft.raidDay}
            aria-invalid={postErrors.raidDay ? 'true' : undefined}
            aria-describedby={postErrors.raidDay ? 'c-day-err' : undefined}
          >
            {#each officerDays as d}<option value={d}>{d}</option>{/each}
          </select>
          {#if postErrors.raidDay}<span id="c-day-err" class="err">{postErrors.raidDay}</span>{/if}
        </div>
      {/if}
    </div>
    <label class="check"><input type="checkbox" bind:checked={draft.toDiscord} /> Also post to Discord</label>
    <div><button class="btn primary" type="submit">Publish post</button></div>
    {#if composeNote}<p role="status">{composeNote}</p>{/if}
  </form>
</section>

<section id="highlights" class="card" aria-labelledby="highlights-h">
  <h2 id="highlights-h">Highlights review</h2>
  {#if hlNote}<p role="status">{hlNote}</p>{/if}
  <div class="cards">
    {#each submitted as h (h.id)}
      <article class="app">
        <ClipPlayer
          provider={h.provider}
          clipId={h.clipId}
          title={h.title}
          meta="{h.boss ?? 'No boss'} · by {h.submittedBy} · {PROVIDER_LABELS[h.provider]}"
        />
        <div class="actions">
          <button type="button" class="btn primary" onclick={() => review(h.id, 'public')}>Publish public</button>
          <button type="button" class="btn" onclick={() => review(h.id, 'guild')}>Publish to guild</button>
          <button type="button" class="btn danger" onclick={() => review(h.id, 'reject')}>Reject</button>
        </div>
      </article>
    {:else}
      <p class="muted">No clips waiting.</p>
    {/each}
  </div>
</section>

<section id="spotlights" class="card" aria-labelledby="spotlights-h">
  <h2 id="spotlights-h">Spotlights</h2>
  {#if spotNote}<p role="status">{spotNote}</p>{/if}
  <div class="cards">
    {#each community.spotlights as s (s.id)}
      <article class="app">
        <header class="app-head">
          <h3>{s.characterName}: {s.headline}</h3>
        </header>
        <p>
          <span class="pill">{s.status === 'draft' ? 'Draft' : s.status === 'published' ? 'Published' : 'Retired'}</span>
          <span class="pill consent-{s.consent}">{CONSENT_LABELS[s.consent]}</span>
        </p>
        <p class="muted small">By {s.writtenBy}</p>
        <div class="actions">
          {#if s.status === 'draft'}
            <button
              type="button"
              class="btn primary"
              disabled={s.consent !== 'granted'}
              onclick={() => setSpotlight(s.id, 'published')}>Publish</button
            >
            {#if s.consent !== 'granted'}<span class="muted small">Waits for {s.memberName}’s consent.</span>{/if}
          {:else if s.status === 'published'}
            <button type="button" class="btn" onclick={() => setSpotlight(s.id, 'retired')}>Retire</button>
          {/if}
        </div>
      </article>
    {/each}
  </div>
</section>

<style>
  .sections {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
    margin-bottom: 1rem;
    position: sticky;
    top: 0;
    background: var(--bg);
    padding: 0.5rem 0;
    z-index: 1;
  }
  section { margin-bottom: 1rem; scroll-margin-top: 3.5rem; }
  .group { font-size: 0.95rem; margin: 1rem 0 0.5rem; }
  .cards { display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr)); }
  .app, .queued { border: 1px solid var(--line); border-radius: 8px; padding: 0.75rem; min-width: 0; }
  .queued + .queued { margin-top: 0.75rem; }
  .app-head { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem 0.5rem; }
  .app-head h3, .app-head h4 { margin: 0; font-size: 1rem; margin-right: auto; }
  .app p { margin: 0.4rem 0; }
  dl { display: grid; grid-template-columns: auto 1fr; gap: 0.25rem 0.75rem; margin: 0.5rem 0; font-size: 0.9rem; }
  dt { color: var(--muted); }
  dd { margin: 0; min-width: 0; }
  .text { white-space: pre-line; overflow-wrap: anywhere; }
  .events { margin: 0.4rem 0 0; padding-left: 1.2rem; font-size: 0.85rem; display: grid; gap: 0.2rem; }
  summary { cursor: pointer; color: var(--muted); font-size: 0.9rem; }
  .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; margin-top: 0.6rem; }
  .room { background: #1f3a4a; color: #9fd3f0; }
  .edited { background: #3b3320; color: var(--warn); }
  .status-applied { background: #3b3320; color: var(--warn); }
  .status-accepted, .consent-granted { background: #24402c; color: var(--accent); }
  .status-declined, .consent-declined { background: #402624; color: #f0a39c; }
  form { display: grid; gap: 0.9rem; max-width: 40rem; }
  .row { display: flex; flex-wrap: wrap; gap: 1rem; }
  .check { display: inline-flex; gap: 0.4rem; align-items: center; }
  .over { color: var(--bad); }
  .small { font-size: 0.8rem; }
</style>
